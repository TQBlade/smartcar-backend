# backend/core/auditoria_utils.py
import json
from core.db.connection import get_connection

def registrar_auditoria_global(id_usuario, entidad, id_entidad, accion, datos_previos=None, datos_nuevos=None):
    """
    Registra la auditoría usando la hora de la base de datos (que ya está configurada en Colombia).
    """
    if not id_usuario:
        return

    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Usamos CURRENT_TIMESTAMP. Al tener la conexión con 'SET TIME ZONE', guardará la hora correcta.
        query = """
            INSERT INTO auditoria (id_usuario, entidad, id_entidad, accion, datos_previos, datos_nuevos, fecha_hora)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        
        val_ant = json.dumps(datos_previos, default=str) if datos_previos else None
        val_nue = json.dumps(datos_nuevos, default=str) if datos_nuevos else None
        
        cur.execute(query, (id_usuario, entidad, id_entidad, accion, val_ant, val_nue))
        conn.commit()

    except Exception as e:
        print(f"❌ Error guardando auditoría: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()