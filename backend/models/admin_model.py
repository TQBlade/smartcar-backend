# backend/models/admin_model.py
import json
from backend.core.db.connection import get_connection
from psycopg2.extras import RealDictCursor
# --- IMPORTAR AUDITORÍA ---
from backend.core.auditoria_utils import registrar_auditoria_global

# ==========================================================
# 1. DASHBOARD BÁSICO (KPIs)
# ==========================================================
def obtener_datos_dashboard():
    """Resumen de datos generales para administrador"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM vehiculo;")
        total_vehiculos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM acceso;")
        total_accesos = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM alerta;")
        total_alertas = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"total_vehiculos": total_vehiculos, "total_accesos": total_accesos, "total_alertas": total_alertas}
    except Exception as e:
        print("❌ Error en dashboard:", e)
        return {}

def obtener_accesos_detalle():
    """Lista todos los accesos recientes"""
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT v.placa, v.tipo, v.color, p.nombre AS propietario, a.resultado, 
                   TO_CHAR(a.fecha_hora, 'YYYY-MM-DD HH24:MI') as fecha
            FROM acceso a
            JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            JOIN persona p ON v.id_persona = p.id_persona
            ORDER BY a.fecha_hora DESC;
        """)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        print("❌ Error en accesos:", e)
        return []

# ==========================================================
# 2. GESTIÓN DE PERSONAL (VIGILANTES/ADMINS)
# ==========================================================

def obtener_todos_vigilantes():
    """
    Obtiene la lista combinando datos de 'vigilante' y 'tmusuarios'.
    """
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                v.id_vigilante, 
                v.nombre, 
                v.doc_identidad, 
                v.telefono, 
                v.estado, 
                r.nombre_rol,
                v.id_rol,
                COALESCE(t.usuario, 'Sin usuario') as usuario,
                COALESCE(t.clave, '') as clave, 
                t.nu as id_usuario
            FROM vigilante v
            JOIN rol r ON v.id_rol = r.id_rol
            LEFT JOIN tmusuarios t ON UPPER(v.nombre) = UPPER(t.nombre)
            WHERE v.estado = 1
            ORDER BY v.id_vigilante DESC;
        """
        cur.execute(query)
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        print("❌ Error listando personal:", e)
        return []

def registrar_vigilante_completo(data, id_admin_responsable):
    """
    Registra Personal + Auditoría.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        id_rol_recibido = int(data['id_rol'])
        nivel_acceso = 1 if id_rol_recibido == 1 else 0

        # 1. INSERTAR EN TABLA 'vigilante'
        sql_vigilante = """
            INSERT INTO vigilante (nombre, doc_identidad, telefono, id_rol, estado)
            VALUES (%s, %s, %s, %s, 1)
            RETURNING id_vigilante
        """
        cur.execute(sql_vigilante, (
            data['nombre'].upper(),
            data['doc_identidad'],
            data['telefono'],
            id_rol_recibido
        ))
        nuevo_id = cur.fetchone()[0]

        # 2. INSERTAR EN TABLA 'tmusuarios'
        sql_usuario = """
            INSERT INTO tmusuarios (nombre, usuario, clave, nivel, fkcods)
            VALUES (%s, %s, %s, %s, 1)
        """
        cur.execute(sql_usuario, (
            data['nombre'].upper(),
            data['usuario'], 
            data['clave'], 
            nivel_acceso
        ))

        conn.commit()
        cur.close()

        # 3. AUDITORÍA
        registrar_auditoria_global(
            id_usuario=id_admin_responsable,
            entidad="PERSONAL",
            id_entidad=nuevo_id,
            accion="CREAR_PERSONAL",
            datos_nuevos={
                "nombre": data['nombre'], 
                "rol": "Admin" if id_rol_recibido==1 else "Vigilante",
                "usuario": data['usuario']
            }
        )

        return True

    except Exception as e:
        if conn: conn.rollback()
        print("❌ Error registrando personal:", e)
        return False
    finally:
        if conn: conn.close()

def actualizar_vigilante_completo(id_vigilante, data, id_admin_responsable):
    """
    Actualiza Personal + Auditoría.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Obtener datos ANTERIORES (para auditoría y buscar en tmusuarios)
        cur_lectura = conn.cursor(cursor_factory=RealDictCursor)
        cur_lectura.execute("SELECT * FROM vigilante WHERE id_vigilante = %s", (id_vigilante,))
        datos_previos = cur_lectura.fetchone()
        cur_lectura.close()

        if not datos_previos: return False
        nombre_anterior = datos_previos['nombre']

        # 2. Actualizar tabla VIGILANTE
        cur.execute("""
            UPDATE vigilante 
            SET nombre=%s, doc_identidad=%s, telefono=%s, id_rol=%s 
            WHERE id_vigilante=%s
        """, (data['nombre'].upper(), data['doc_identidad'], data['telefono'], data['id_rol'], id_vigilante))

        # 3. Actualizar tabla TMUSUARIOS
        nivel = 1 if int(data['id_rol']) == 1 else 0
        
        sql_user = "UPDATE tmusuarios SET nombre=%s, usuario=%s, nivel=%s"
        params_user = [data['nombre'].upper(), data['usuario'], nivel]
        
        if data.get('clave') and data['clave'].strip() != "":
            sql_user += ", clave=%s"
            params_user.append(data['clave'])
        
        sql_user += " WHERE UPPER(nombre) = UPPER(%s)"
        params_user.append(nombre_anterior.upper())

        cur.execute(sql_user, tuple(params_user))

        conn.commit()
        cur.close()

        # 4. AUDITORÍA
        registrar_auditoria_global(
            id_usuario=id_admin_responsable,
            entidad="PERSONAL",
            id_entidad=id_vigilante,
            accion="ACTUALIZAR_PERSONAL",
            datos_previos=datos_previos,
            datos_nuevos=data
        )

        return True
    except Exception as e:
        if conn: conn.rollback()
        print("❌ Error actualizando personal:", e)
        return False
    finally:
        if conn: conn.close()

def eliminar_vigilante_completo(id_vigilante, id_admin_responsable):
    """
    Borrado lógico de Personal + Auditoría.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. Obtener datos para auditoría
        cur_lectura = conn.cursor(cursor_factory=RealDictCursor)
        cur_lectura.execute("SELECT * FROM vigilante WHERE id_vigilante = %s", (id_vigilante,))
        datos_previos = cur_lectura.fetchone()
        cur_lectura.close()

        if not datos_previos: return False
        nombre = datos_previos['nombre']

        # 2. Desactivar en VIGILANTE
        cur.execute("UPDATE vigilante SET estado = 0 WHERE id_vigilante = %s", (id_vigilante,))

        # 3. Desactivar en TMUSUARIOS
        cur.execute("UPDATE tmusuarios SET fkcods = 0 WHERE UPPER(nombre) = UPPER(%s)", (nombre,))

        conn.commit()
        cur.close()

        # 4. AUDITORÍA
        registrar_auditoria_global(
            id_usuario=id_admin_responsable,
            entidad="PERSONAL",
            id_entidad=id_vigilante,
            accion="ELIMINAR_PERSONAL",
            datos_previos=datos_previos
        )

        return True
    except Exception as e:
        if conn: conn.rollback()
        print("❌ Error eliminando personal:", e)
        return False
    finally:
        if conn: conn.close()

# ==========================================================
# 3. REPORTES GERENCIALES
# ==========================================================

def obtener_data_reporte_completo(fecha_inicio, fecha_fin):
    data = { "estadisticas": {}, "accesos": [], "alertas_resueltas": [], "novedades": [], "hora_pico": None }
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. ESTADÍSTICAS
        sql_stats = """
            SELECT 
                COUNT(*) as total_movimientos,
                SUM(CASE WHEN resultado ILIKE '%%Autorizado%%' THEN 1 ELSE 0 END) as autorizados,
                SUM(CASE WHEN resultado ILIKE '%%Denegado%%' THEN 1 ELSE 0 END) as denegados
            FROM acceso WHERE DATE(fecha_hora) BETWEEN %s AND %s
        """
        cur.execute(sql_stats, (fecha_inicio, fecha_fin))
        data["estadisticas"] = cur.fetchone()

        # 2. HORA PICO
        sql_pico = """
            SELECT EXTRACT(HOUR FROM fecha_hora) as hora, COUNT(*) as cantidad
            FROM acceso WHERE DATE(fecha_hora) BETWEEN %s AND %s
            GROUP BY hora ORDER BY cantidad DESC LIMIT 1
        """
        cur.execute(sql_pico, (fecha_inicio, fecha_fin))
        data["hora_pico"] = cur.fetchone()

        # 3. DETALLE DE ACCESOS
        sql_accesos = """
            SELECT TO_CHAR(a.fecha_hora, 'YYYY-MM-DD HH24:MI') as fecha, v.placa, v.tipo, a.resultado, COALESCE(u.nombre, 'Sistema') as vigilante
            FROM acceso a
            LEFT JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            LEFT JOIN tmusuarios u ON a.id_vigilante = u.nu
            WHERE DATE(a.fecha_hora) BETWEEN %s AND %s ORDER BY a.fecha_hora DESC
        """
        cur.execute(sql_accesos, (fecha_inicio, fecha_fin))
        data["accesos"] = cur.fetchall()

        # 4. ALERTAS RESUELTAS
        sql_alertas = """
            SELECT TO_CHAR(au.fecha_hora, 'YYYY-MM-DD HH24:MI') as fecha_resolucion, u.nombre as resolutor, au.datos_previos, au.datos_nuevos
            FROM auditoria au JOIN tmusuarios u ON au.id_usuario = u.nu
            WHERE au.entidad = 'ALERTA' AND au.accion = 'RESOLVER_ALERTA' AND DATE(au.fecha_hora) BETWEEN %s AND %s
        """
        cur.execute(sql_alertas, (fecha_inicio, fecha_fin))
        data["alertas_resueltas"] = cur.fetchall()

        # 5. NOVEDADES
        sql_novedades = """
            SELECT TO_CHAR(n.fecha_hora, 'YYYY-MM-DD HH24:MI') as fecha, n.asunto, n.descripcion, u.nombre as vigilante
            FROM novedad n JOIN tmusuarios u ON n.id_usuario = u.nu
            WHERE DATE(n.fecha_hora) BETWEEN %s AND %s ORDER BY n.fecha_hora DESC
        """
        cur.execute(sql_novedades, (fecha_inicio, fecha_fin))
        data["novedades"] = cur.fetchall()

        cur.close()
        return data
    except Exception as e:
        print(f"Error generando reporte: {e}")
        return None
    finally:
        if conn: conn.close()

# Compatibilidad legacy
def registrar_vigilante(nombre, doc, telefono, id_rol): return False