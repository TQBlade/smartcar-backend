# backend/core/controller_calendario.py

from backend.core.db.connection import get_connection
from psycopg2.extras import RealDictCursor
from backend.core.auditoria_utils import registrar_auditoria_global

# ==========================================================
# 1. OBTENER EVENTOS (Para el Calendario)
# ==========================================================
def obtener_eventos_controller():
    """
    Obtiene todos los eventos para mostrarlos en el calendario.
    Formatea las fechas como cadenas ISO para que React las entienda.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                id_evento,
                titulo,
                descripcion,
                TO_CHAR(fecha_inicio, 'YYYY-MM-DD"T"HH24:MI:SS') as start, -- Formato ISO
                TO_CHAR(fecha_fin, 'YYYY-MM-DD"T"HH24:MI:SS') as end,     -- Formato ISO
                ubicacion,
                categoria,
                verificado,
                id_creador
            FROM evento
            ORDER BY fecha_inicio DESC;
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo eventos: {e}")
        return []
    finally:
        if conn: conn.close()

# ==========================================================
# 2. VERIFICAR EVENTOS ACTIVOS (Para lógica de Invitados)
# ==========================================================
def hay_evento_activo_controller():
    """
    Verifica si hay algún evento activo en este momento (Fecha Actual entre Inicio y Fin).
    Retorna True si hay evento, False si no.
    Útil para permitir acceso a invitados.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Consultamos si hay al menos un evento activo ahora mismo
        query = """
            SELECT COUNT(*) 
            FROM evento 
            WHERE NOW() BETWEEN fecha_inicio AND fecha_fin
        """
        cur.execute(query)
        cantidad = cur.fetchone()[0]
        
        return cantidad > 0
    except Exception as e:
        print(f"Error verificando eventos activos: {e}")
        return False
    finally:
        if conn: conn.close()

# ==========================================================
# 3. CREAR EVENTO (Con Auditoría)
# ==========================================================
def crear_evento_controller(data, usuario_actual):
    """
    Crea un nuevo evento (Solo Admin).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Obtenemos el ID del usuario que crea el evento (id_audit = nu de tmusuarios)
        id_creador = usuario_actual.get('id_audit')

        query = """
            INSERT INTO evento (titulo, descripcion, fecha_inicio, fecha_fin, ubicacion, categoria, id_creador)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id_evento
        """
        cursor.execute(query, (
            data.get('titulo'),
            data.get('descripcion'),
            data.get('start'), # El frontend debe enviar 'start' (fecha inicio)
            data.get('end'),   # El frontend debe enviar 'end' (fecha fin)
            data.get('ubicacion'),
            data.get('categoria'),
            id_creador
        ))
        
        id_nuevo = cursor.fetchone()[0]
        conn.commit()
        
        # Auditoría
        registrar_auditoria_global(
            id_usuario=id_creador,
            entidad="EVENTO",
            id_entidad=id_nuevo,
            accion="CREAR_EVENTO",
            datos_nuevos=data
        )

        return id_nuevo
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error creando evento: {e}")
        raise e
    finally:
        if conn: conn.close()

# ==========================================================
# 4. ACTUALIZAR EVENTO
# ==========================================================
def actualizar_evento_controller(id_evento, data):
    """
    Actualiza un evento existente.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE evento
            SET titulo = %s, descripcion = %s, fecha_inicio = %s, fecha_fin = %s, ubicacion = %s, categoria = %s
            WHERE id_evento = %s
        """
        cursor.execute(query, (
            data.get('titulo'),
            data.get('descripcion'),
            data.get('start'),
            data.get('end'),
            data.get('ubicacion'),
            data.get('categoria'),
            id_evento
        ))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error actualizando evento: {e}")
        raise e
    finally:
        if conn: conn.close()

# ==========================================================
# 5. ELIMINAR EVENTO (Corregido con Auditoría)
# ==========================================================
def eliminar_evento_controller(id_evento, usuario_actual):
    """
    Elimina un evento y registra la auditoría.
    """
    conn = None
    try:
        conn = get_connection()
        
        # 1. Obtener datos del evento ANTES de borrar (para la auditoría)
        cur_lectura = conn.cursor(cursor_factory=RealDictCursor)
        cur_lectura.execute("SELECT * FROM evento WHERE id_evento = %s", (id_evento,))
        evento_anterior = cur_lectura.fetchone()
        cur_lectura.close()

        if not evento_anterior:
            return False # El evento no existe

        # 2. Eliminar el evento
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evento WHERE id_evento = %s", (id_evento,))
        conn.commit()

        # 3. Registrar Auditoría
        # Convertimos fechas a string para evitar errores de serialización JSON
        if evento_anterior.get('fecha_inicio'):
            evento_anterior['fecha_inicio'] = str(evento_anterior['fecha_inicio'])
        if evento_anterior.get('fecha_fin'):
            evento_anterior['fecha_fin'] = str(evento_anterior['fecha_fin'])

        id_usuario = usuario_actual.get('id_audit') if usuario_actual else None

        registrar_auditoria_global(
            id_usuario=id_usuario,
            entidad="EVENTO",
            id_entidad=id_evento,
            accion="ELIMINAR_EVENTO",
            datos_previos=evento_anterior
        )
        
        return True

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error eliminando evento: {e}")
        raise e
    finally:
        if conn: conn.close()

# ==========================================================
# 6. VERIFICAR EVENTO (Vigilante)
# ==========================================================
def verificar_evento_controller(id_evento, estado_verificacion):
    """
    Permite al vigilante marcar un evento como 'Verificado' (En curso/Iniciado).
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "UPDATE evento SET verificado = %s WHERE id_evento = %s"
        cursor.execute(query, (estado_verificacion, id_evento))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error verificando evento: {e}")
        raise e
    finally:
        if conn: conn.close()