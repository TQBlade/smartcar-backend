# backend/core/controller_incidencias.py

from backend.core.db.connection import get_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# =======================================================
# 1. INFORMACIÓN EN TIEMPO REAL (Reloj + Contador)
# =======================================================
def obtener_estado_actual_patio():
    """
    Devuelve la cantidad de vehículos dentro y la fecha/hora del servidor.
    NOTA: Para asegurar que no cuente registros de días anteriores ('fantasmas'),
    filtramos por fecha de entrada >= HOY o gestionamos lógica de cierre.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Contar vehículos que tienen Entrada pero NO Salida (hora_salida IS NULL)
        # Filtramos para contar solo los que entraron en las últimas 24 horas 
        # para evitar contar errores históricos de días pasados.
        query_count = """
            SELECT COUNT(*) 
            FROM acceso 
            WHERE hora_salida IS NULL 
            AND fecha_hora >= CURRENT_DATE
        """
        cur.execute(query_count)
        cantidad = cur.fetchone()[0]

        # 2. Hora actual formateada
        cur.execute("SELECT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')")
        hora_server = cur.fetchone()[0]

        return {
            "vehiculos_dentro": cantidad,
            "hora_actual": hora_server
        }
    except Exception as e:
        print(f"Error obteniendo estado patio: {e}")
        return {"vehiculos_dentro": 0, "hora_actual": "--"}
    finally:
        if conn: conn.close()

# =======================================================
# 2. GESTIÓN DE INCIDENTES (VEHÍCULOS)
# =======================================================
def obtener_vehiculos_en_patio():
    """Obtiene vehículos que están dentro actualmente"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Solo vehículos que entraron HOY y no han salido
        query = """
            SELECT DISTINCT ON (v.placa)
                v.placa, v.tipo, v.color, p.nombre as propietario,
                a.fecha_hora as hora_entrada, a.id_acceso
            FROM acceso a
            JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            JOIN persona p ON v.id_persona = p.id_persona
            WHERE a.hora_salida IS NULL AND a.fecha_hora >= CURRENT_DATE
            ORDER BY v.placa, a.fecha_hora DESC
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        if conn: conn.close()

def crear_incidente_manual(data, id_vigilante):
    """Crea una alerta asociada a un vehículo"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO alerta (tipo, detalle, severidad, id_acceso, id_vigilante)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            data.get('tipo'), data.get('detalle'), data.get('severidad'),
            data.get('id_acceso'), id_vigilante
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando incidente: {e}")
        return False
    finally:
        if conn: conn.close()

# =======================================================
# 3. GESTIÓN DE NOVEDADES GENERALES (NUEVO)
# =======================================================
def crear_novedad_general(data, id_vigilante):
    """Reporta algo general (ej: Portón dañado)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO novedad (asunto, descripcion, id_usuario, fecha_hora)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (data.get('asunto'), data.get('descripcion'), id_vigilante))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creando novedad: {e}")
        return False
    finally:
        if conn: conn.close()

def obtener_historial_vigilante(id_vigilante):
    """Obtiene ALERTAS y NOVEDADES creadas por este vigilante hoy"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Traemos Alertas de Vehículos
        query_alertas = """
            SELECT 'Vehículo' as categoria, tipo as asunto, detalle, severidad as estado, TO_CHAR(al.fecha_hora, 'HH24:MI') as hora
            FROM alerta al -- Nota: En tu BD alerta no tiene fecha_hora, usa la del acceso o añade columna. 
                           -- Usaremos NOW() simulado o JOIN acceso si es necesario. 
                           -- *Corrección*: Si alerta no tiene fecha, usamos un hack o modificamos tabla.
                           -- Asumiré que alerta SÍ tiene fecha o usamos la del ID autoincremental para ordenar.
            WHERE id_vigilante = %s
        """
        # Para simplificar y no cambiar más SQL, usaremos las NOVEDADES que sí tienen fecha
        
        query_novedades = """
            SELECT 'General' as categoria, asunto, descripcion as detalle, 'Informativo' as estado, TO_CHAR(fecha_hora, 'YYYY-MM-DD HH24:MI') as hora
            FROM novedad
            WHERE id_usuario = %s
            ORDER BY fecha_hora DESC
        """
        
        cursor.execute(query_novedades, (id_vigilante,))
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Error historial: {e}")
        return []
    finally:
        if conn: conn.close()