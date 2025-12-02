# backend/models/acceso.py
from backend.core.db.connection import get_connection

def verificar_vehiculo_dentro(placa):
    """
    Busca si hay un registro de esta placa que tenga fecha de entrada 
    pero NO tenga fecha de salida (hora_salida IS NULL).
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Buscamos la última entrada que tenga salida NULL (vacía)
    sql = """
        SELECT a.id_acceso 
        FROM acceso a
        JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
        WHERE v.placa = %s AND a.hora_salida IS NULL
    """
    cur.execute(sql, (placa,))
    resultado = cur.fetchone()
    cur.close()
    conn.close()
    
    if resultado:
        return resultado[0] # Retorna el ID del acceso pendiente
    return None

def registrar_salida_db(id_acceso):
    """
    Actualiza el registro existente poniendo la hora actual en hora_salida.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Actualizamos la hora de salida y el resultado
        sql = """
            UPDATE acceso 
            SET hora_salida = CURRENT_TIMESTAMP, 
                resultado = 'Salida Exitosa'
            WHERE id_acceso = %s
        """
        cur.execute(sql, (id_acceso,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error registrando salida: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def registrar_entrada_db(placa, id_vigilante):
    """
    Crea un nuevo registro de acceso.
    CORREGIDO: No inserta id_persona (no existe en tabla acceso).
    CORREGIDO: Inserta id_punto (obligatorio).
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1. Obtener ID Vehiculo (validamos que exista)
        cur.execute("SELECT id_vehiculo FROM vehiculo WHERE placa = %s", (placa,))
        vehiculo = cur.fetchone()
        
        if not vehiculo:
            return {"status": "error", "mensaje": "Vehículo no registrado"}

        id_vehiculo = vehiculo[0]
        
        # DEFINICIÓN DE PUNTO DE CONTROL
        # Según tu SQL: id_punto 1 = 'Entrada'
        ID_PUNTO_ENTRADA = 1 

        # 2. Insertar Entrada
        # Eliminamos 'id_persona' de la lista de columnas
        # Agregamos 'id_punto'
        sql = """
            INSERT INTO acceso (id_vehiculo, id_punto, id_vigilante, fecha_hora, resultado, hora_salida)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 'Acceso Concedido - Entrada', NULL)
        """
        
        cur.execute(sql, (id_vehiculo, ID_PUNTO_ENTRADA, id_vigilante))
        conn.commit()
        
        return {"status": "ok", "mensaje": "Entrada registrada"}
    except Exception as e:
        conn.rollback()
        print(f"Error SQL registrar_entrada: {e}")
        return {"status": "error", "mensaje": str(e)}
    finally:
        cur.close()
        conn.close()