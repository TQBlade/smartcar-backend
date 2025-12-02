from core.db import get_db_connection

def create_alerta(tipo, detalle, severidad, oid_acceso, oid_vigilante):
    """
    Registra una nueva alerta de seguridad.
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        query = """
            INSERT INTO alerta (tipo, detalle, severidad, oid_acceso, oid_vigilante)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_alerta;
        """
        cur.execute(query, (tipo, detalle, severidad, oid_acceso, oid_vigilante))
        id_alerta = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return id_alerta
    except Exception as e:
        print(f"Error al crear alerta: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()