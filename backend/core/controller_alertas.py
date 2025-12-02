# backend/core/controller_alertas.py

from core.db.connection import get_connection
from psycopg2.extras import RealDictCursor
from core.auditoria_utils import registrar_auditoria_global

def obtener_alertas_controller():
    """
    Obtiene todas las alertas activas con datos detallados:
    - Nombre del Vigilante (quien reportó).
    - Placa del Vehículo implicado.
    - Fecha y Hora.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # CORRECCIÓN DE CONSULTA:
        # 1. Unimos con tmusuarios para el nombre del vigilante.
        # 2. Unimos con acceso -> vehiculo para la placa.
        query = """
            SELECT 
                al.id_alerta,
                al.tipo,
                al.detalle,
                al.severidad,
                TO_CHAR(acc.fecha_hora, 'YYYY-MM-DD HH12:MI AM') as fecha_hora,
                u.nombre as nombre_vigilante,
                v.placa,
                v.tipo as tipo_vehiculo,
                v.color
            FROM alerta al
            JOIN acceso acc ON al.id_acceso = acc.id_acceso
            JOIN vehiculo v ON acc.id_vehiculo = v.id_vehiculo
            JOIN tmusuarios u ON al.id_vigilante = u.nu
            ORDER BY acc.fecha_hora DESC;
        """
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error obteniendo alertas: {e}")
        return []
    finally:
        if conn: conn.close()

def eliminar_alerta_controller(id_alerta, usuario_actual, accion_resolucion="Resolución General"):
    """
    Elimina una alerta (la marca como resuelta) y registra en auditoría la acción tomada.
    """
    conn = None
    try:
        conn = get_connection()
        
        # 1. Obtener datos antes de borrar
        cursor_lec = conn.cursor(cursor_factory=RealDictCursor)
        cursor_lec.execute("SELECT * FROM alerta WHERE id_alerta = %s", (id_alerta,))
        alerta_prev = cursor_lec.fetchone()
        cursor_lec.close()

        if not alerta_prev:
            return False

        # 2. Eliminar la alerta
        cursor = conn.cursor()
        cursor.execute("DELETE FROM alerta WHERE id_alerta = %s", (id_alerta,))
        conn.commit()

        # 3. Registrar Auditoría con la ACCIÓN TOMADA
        registrar_auditoria_global(
            id_usuario=usuario_actual['id_audit'],
            entidad="ALERTA",
            id_entidad=id_alerta,
            accion="RESOLVER_ALERTA",
            datos_previos=alerta_prev,
            datos_nuevos={"resolucion": accion_resolucion, "estado": "CERRADA"}
        )
        return True
    except Exception as e:
        print(f"Error eliminando alerta: {e}")
        return False
    finally:
        if conn: conn.close()

# (Opcional) Mantener esta si la usas en otro lado, si no, se puede borrar.
def obtener_mis_reportes_controller(id_vigilante):
    return []