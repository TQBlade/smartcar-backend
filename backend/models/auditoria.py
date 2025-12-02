# backend/models/auditoria.py
import sys
import os
from psycopg2.extras import RealDictCursor

# Asegurar que la ruta 'backend' esté en sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.db.connection import get_connection

def obtener_historial_auditoria():
    """
    Obtiene todos los registros del historial de auditoría.
    SOLUCIÓN DE HORA: Usamos TO_CHAR para formatear la fecha directamente desde la BD.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # --- AQUÍ ESTÁ EL CAMBIO CLAVE (TO_CHAR) ---
        query = """
            SELECT 
                a.id_auditoria,
                TO_CHAR(a.fecha_hora, 'YYYY-MM-DD HH12:MI:SS AM') as fecha_hora, -- Formato fijo texto
                u.nombre AS nombre_vigilante,
                a.entidad,
                a.id_entidad,
                a.accion,
                a.datos_previos,
                a.datos_nuevos,
                a.id_usuario
            FROM 
                auditoria a
            LEFT JOIN 
                tmusuarios u ON a.id_usuario = u.nu
            ORDER BY 
                a.fecha_hora DESC;
        """
        
        cur.execute(query)
        historial = cur.fetchall()
        
        cur.close()
        return historial
        
    except Exception as e:
        print(f"❌ Error en models/auditoria.py: {e}")
        raise e
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    try:
        print("Probando obtener_historial_auditoria...")
        historial = obtener_historial_auditoria()
        if historial:
            print(f"✅ Se obtuvieron {len(historial)} registros.")
            print("Fecha del primer registro:", historial[0]['fecha_hora'])
    except Exception as e:
        print(f"⚠️  Error en la prueba: {e}")