# backend/core/controller_personas.py
# Lógica de negocio para el CRUD de Personas y Auditoría (Alineado con bd_carros.sql)

import json
# CORREGIDO: Importación del modelo con la ruta completa
from backend.models.persona import Persona 
from core.db.connection import get_connection
# CORREGIDO: Importación de Psycopg2 para cursores de diccionario
from psycopg2.extras import RealDictCursor
from backend.core.auditoria_utils import registrar_auditoria_global
# --- Función de Auditoría (Corregida para bd_carros.sql) ---

def _registrar_auditoria(id_vigilante, entidad, id_entidad, accion, datos_previos=None, datos_nuevos=None):
    """
    Función helper para insertar un registro de auditoría.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # --- CAMBIO CLAVE AQUÍ ---
        # La columna ahora se llama 'id_usuario' en la BD
        query = """
        INSERT INTO auditoria (id_usuario, entidad, id_entidad, accion, datos_previos, datos_nuevos)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        # -------------------------
        
        val_ant_str = json.dumps(datos_previos, default=str) if datos_previos else None
        val_nue_str = json.dumps(datos_nuevos, default=str) if datos_nuevos else None
        
        # Pasamos el 'id_vigilante' (que es el id_audit/nu) a la columna 'id_usuario'
        cursor.execute(query, (id_vigilante, entidad, id_entidad, accion, val_ant_str, val_nue_str))
        conn.commit()
        print(f"[Auditoria] Registro creado: {accion} en {entidad} (ID: {id_entidad}) por usuario {id_vigilante}")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error al registrar auditoría: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# --- Funciones del CRUD de Personas (Corregido) ---

def obtener_personas_controller():
    """
    Obtiene todas las personas activas.
    """
    conn = None
    cursor = None
    try:
        # CORREGIDO: Llamada a la función de conexión correcta
        conn = get_connection()
        # CORREGIDO: Sintaxis de cursor para Psycopg2
        cursor = conn.cursor(cursor_factory=RealDictCursor) 
        
        # estado = 1 es 'ACTIVO' según la tabla tmstatus
        cursor.execute("SELECT * FROM persona WHERE estado = 1")
        personas_db = cursor.fetchall()
        
        # Devolvemos la lista de diccionarios directamente
        return personas_db
        
    except Exception as e:
        print(f"Error en obtener_personas_controller: {e}")
        raise Exception(f"Error interno al obtener personas: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# CORREGIDO: La función ahora recibe 'usuario_actual' (del token) en lugar de 'headers'
def crear_persona_controller(data, usuario_actual):
    """
    Crea una nueva persona.
    """
    conn = None
    cursor = None
    try:
        nueva_persona = Persona.from_dict(data)
        
        # CORREGIDO: Obtenemos el ID de auditoría del token (como lo definimos en el Paso 1)
        id_vigilante_actual = usuario_actual['id_audit']
        if not id_vigilante_actual:
            raise ValueError("Token inválido o ID de auditoría ausente")

        # CORREGIDO: Llamada a la función de conexión correcta
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO persona (doc_identidad, nombre, tipo_persona, estado)
        VALUES (%s, %s, %s, %s)
        RETURNING id_persona
        """
        cursor.execute(query, (
            nueva_persona.doc_identidad,
            nueva_persona.nombre,
            nueva_persona.tipo_persona,
            nueva_persona.estado
        ))
        
        # CORREGIDO: Sintaxis de Psycopg2 para obtener el ID devuelto
        id_persona_nueva = cursor.fetchone()[0]
        conn.commit()
        
        # Registrar Auditoría
        nueva_persona.id_persona = id_persona_nueva
        registrar_auditoria_global(
            id_usuario=id_vigilante_actual, # Asegúrate de usar el ID del usuario logueado
            entidad='persona',
            id_entidad=id_persona_nueva,
            accion='CREAR',
            datos_nuevos=nueva_persona.to_dict()
        )
        
        return id_persona_nueva

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en crear_persona_controller: {e}")
        raise Exception(f"Error interno al crear persona: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# CORREGIDO: La función ahora recibe 'usuario_actual'
def actualizar_persona_controller(id_persona, data, usuario_actual):
    """
    Actualiza una persona existente.
    """
    conn = None
    cursor = None
    cursor_dict = None
    try:
        # CORREGIDO: Obtenemos el ID de auditoría del token
        id_vigilante_actual = usuario_actual['id_audit']
        if not id_vigilante_actual:
            raise ValueError("Token inválido o ID de auditoría ausente")

        # CORREGIDO: Llamada a la función de conexión correcta
        conn = get_connection()
        
        # 1. Obtener estado ANTERIOR (para Auditoría)
        # CORREGIDO: Sintaxis de cursor para Psycopg2
        cursor_dict = conn.cursor(cursor_factory=RealDictCursor)
        cursor_dict.execute("SELECT * FROM persona WHERE id_persona = %s", (id_persona,))
        persona_anterior_db = cursor_dict.fetchone()
        cursor_dict.close()
        
        if not persona_anterior_db:
            raise ValueError("Persona no encontrada")
        
        persona_anterior = Persona(**persona_anterior_db)
        
        # 2. Iniciar transacción con cursor estándar
        cursor = conn.cursor()
        persona_actualizada = Persona.from_dict(data)
        persona_actualizada.id_persona = id_persona

        # 3. Ejecutar la actualización
        query = """
        UPDATE persona SET
            doc_identidad = %s,
            nombre = %s,
            tipo_persona = %s,
            estado = %s
        WHERE id_persona = %s
        """
        cursor.execute(query, (
            persona_actualizada.doc_identidad,
            persona_actualizada.nombre,
            persona_actualizada.tipo_persona,
            persona_actualizada.estado,
            id_persona
        ))
        
        conn.commit()

        # 4. Registrar Auditoría
        _registrar_auditoria(
            id_vigilante=id_vigilante_actual,
            entidad='persona',
            id_entidad=id_persona,
            accion='ACTUALIZAR',
            datos_previos=persona_anterior.to_dict(),
            datos_nuevos=persona_actualizada.to_dict()
        )
        
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error en actualizar_persona_controller: {e}")
        raise Exception(f"Error interno al actualizar persona: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def desactivar_persona_controller(id_persona, usuario_actual):
    """
    Desactiva una persona (borrado lógico) actualizando su estado a 0.
    """
    conn = None
    cursor = None
    try:
        id_vigilante_actual = usuario_actual['id_audit']
        conn = get_connection()
        
        # 1. Obtener estado anterior para auditoría
        cursor_dict = conn.cursor(cursor_factory=RealDictCursor)
        cursor_dict.execute("SELECT * FROM persona WHERE id_persona = %s", (id_persona,))
        persona_anterior_db = cursor_dict.fetchone()
        cursor_dict.close()
        
        if not persona_anterior_db:
            raise ValueError("Persona no encontrada")

        persona_anterior = Persona(**persona_anterior_db)
        
        # 2. Ejecutar el borrado lógico (actualizar estado)
        cursor = conn.cursor()
        cursor.execute("UPDATE persona SET estado = 0 WHERE id_persona = %s", (id_persona,))
        conn.commit()

        # 3. Registrar Auditoría
        persona_actualizada = persona_anterior.to_dict()
        persona_actualizada['estado'] = 0 # El nuevo estado
        
        _registrar_auditoria(
            id_vigilante=id_vigilante_actual,
            entidad='persona',
            id_entidad=id_persona,
            accion='DESACTIVAR', # Usamos 'DESACTIVAR' en lugar de 'ELIMINAR'
            datos_previos=persona_anterior.to_dict(),
            datos_nuevos=persona_actualizada
        )
        return True
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en desactivar_persona_controller: {e}")
        raise Exception(f"Error interno al desactivar persona: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()