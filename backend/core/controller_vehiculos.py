# backend/core/controller_vehiculos.py
import json
from backend.models.vehiculo import Vehiculo
from core.db.connection import get_connection
from psycopg2.extras import RealDictCursor
from core.controller_personas import _registrar_auditoria 

def obtener_vehiculos_controller():
    conn = None
    cursor = None
    try:
        conn = get_connection() 
        cursor = conn.cursor(cursor_factory=RealDictCursor) 
        
        query = """
        SELECT 
            v.id_vehiculo, v.placa, v.tipo, v.color, v.id_persona,
            p.nombre AS propietario_nombre, 
            p.doc_identidad AS propietario_doc_identidad
        FROM vehiculo v
        JOIN persona p ON v.id_persona = p.id_persona
        WHERE p.estado = 1; 
        """
        cursor.execute(query)
        vehiculos_db = cursor.fetchall()
        
        vehiculos_lista = []
        for v in vehiculos_db:
            vehiculo_data = {
                "id_vehiculo": v['id_vehiculo'],
                "placa": v['placa'],
                "tipo": v['tipo'],
                "color": v['color'],
                "id_persona": v['id_persona'],
                "propietario": {
                    "id_persona": v['id_persona'],
                    "nombre": v['propietario_nombre'],
                    "doc_identidad": v['propietario_doc_identidad']
                }
            }
            vehiculos_lista.append(vehiculo_data)

        return vehiculos_lista
        
    except Exception as e:
        print(f"Error en obtener_vehiculos_controller: {e}")
        raise Exception(f"Error interno al obtener vehículos: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def crear_vehiculo_controller(data, usuario_actual):
    conn = None
    cursor = None
    try:
        nuevo_vehiculo = Vehiculo.from_dict(data)
        id_vigilante_actual = usuario_actual['id_audit']
        
        if not id_vigilante_actual:
            raise ValueError("Token inválido o ID de auditoría ausente")

        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar si id_persona (propietario) existe
        cursor.execute("SELECT id_persona FROM persona WHERE id_persona = %s AND estado = 1", (nuevo_vehiculo.id_persona,))
        if not cursor.fetchone():
            raise ValueError(f"La Persona (propietario) con ID {nuevo_vehiculo.id_persona} no existe o está inactiva.")
            
        query = """
        INSERT INTO vehiculo (placa, tipo, color, id_persona)
        VALUES (%s, %s, %s, %s)
        RETURNING id_vehiculo
        """
        cursor.execute(query, (
            nuevo_vehiculo.placa,
            nuevo_vehiculo.tipo,
            nuevo_vehiculo.color,
            nuevo_vehiculo.id_persona
        ))
        
        id_vehiculo_nuevo = cursor.fetchone()[0]
        conn.commit()
        
        nuevo_vehiculo.id_vehiculo = id_vehiculo_nuevo
        _registrar_auditoria(
            id_vigilante=id_vigilante_actual,
            entidad='vehiculo',
            id_entidad=id_vehiculo_nuevo,
            accion='CREAR',
            datos_previos=None,
            datos_nuevos=json.dumps(nuevo_vehiculo.to_dict(), default=str) 
        )
        
        return id_vehiculo_nuevo

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en crear_vehiculo_controller: {e}")
        raise Exception(f"Error interno al crear vehículo: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def actualizar_vehiculo_controller(id_vehiculo, data, usuario_actual):
    conn = None
    cursor = None
    cursor_dict = None
    try:
        id_vigilante_actual = usuario_actual['id_audit']
        if not id_vigilante_actual:
            raise ValueError("Token inválido o ID de auditoría ausente")

        conn = get_connection()
        
        # 1. Obtener estado ANTERIOR
        cursor_dict = conn.cursor(cursor_factory=RealDictCursor)
        cursor_dict.execute("SELECT * FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
        vehiculo_anterior_db = cursor_dict.fetchone()
        cursor_dict.close()
        
        if not vehiculo_anterior_db:
            raise ValueError("Vehiculo no encontrado")
        
        vehiculo_anterior = Vehiculo(**vehiculo_anterior_db)
        
        # 2. Preparar datos nuevos
        # Nota: Si usas from_dict, asegúrate de que 'data' tenga todos los campos
        # Si data viene parcial, hay que mezclarla con vehiculo_anterior
        vehiculo_actualizado = Vehiculo.from_dict(data)
        vehiculo_actualizado.id_vehiculo = id_vehiculo

        # Lógica para resolver el ID del dueño si viene la cédula en vez del ID
        cursor = conn.cursor()
        
        if 'cedula_nuevo_dueno' in data and data['cedula_nuevo_dueno']:
            cursor.execute("SELECT id_persona FROM persona WHERE doc_identidad = %s AND estado = 1", (data['cedula_nuevo_dueno'],))
            res_persona = cursor.fetchone()
            if not res_persona:
                raise ValueError(f"No existe persona con cédula {data['cedula_nuevo_dueno']}")
            vehiculo_actualizado.id_persona = res_persona[0]
        
        # Si no se ha definido el id_persona (por ejemplo, viene nulo), mantener el anterior
        if not vehiculo_actualizado.id_persona:
             vehiculo_actualizado.id_persona = vehiculo_anterior.id_persona

        # 3. Verificar existencia del propietario final
        cursor.execute("SELECT id_persona FROM persona WHERE id_persona = %s AND estado = 1", (vehiculo_actualizado.id_persona,))
        if not cursor.fetchone():
            raise ValueError(f"La Persona con ID {vehiculo_actualizado.id_persona} no existe.")

        # 4. Ejecutar la actualización
        query = """
        UPDATE vehiculo SET
            placa = %s,
            tipo = %s,
            color = %s,
            id_persona = %s
        WHERE id_vehiculo = %s
        """
        cursor.execute(query, (
            vehiculo_actualizado.placa,
            vehiculo_actualizado.tipo,
            vehiculo_actualizado.color,
            vehiculo_actualizado.id_persona,
            id_vehiculo
        ))
        
        conn.commit()

        # 5. Registrar Auditoría (Corregido: usaba variables inexistentes)
        _registrar_auditoria(
            id_vigilante=id_vigilante_actual,
            entidad='vehiculo',
            id_entidad=id_vehiculo,
            accion='ACTUALIZAR',
            datos_previos=json.dumps(vehiculo_anterior.to_dict(), default=str),
            datos_nuevos=json.dumps(vehiculo_actualizado.to_dict(), default=str)
        )
        return True

    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en actualizar_vehiculo_controller: {e}")
        raise Exception(f"Error interno al actualizar vehículo: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def eliminar_vehiculo_controller(id_vehiculo, usuario_actual):
    conn = None
    cursor = None
    try:
        id_vigilante_actual = usuario_actual['id_audit']
        conn = get_connection()

        cursor_dict = conn.cursor(cursor_factory=RealDictCursor)
        cursor_dict.execute("SELECT * FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
        vehiculo_anterior_db = cursor_dict.fetchone()
        cursor_dict.close()

        if not vehiculo_anterior_db:
            raise ValueError("Vehiculo no encontrado")

        vehiculo_anterior = Vehiculo(**vehiculo_anterior_db)

        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
        conn.commit()

        _registrar_auditoria(
            id_vigilante=id_vigilante_actual,
            entidad='vehiculo',
            id_entidad=id_vehiculo,
            accion='ELIMINAR',
            datos_previos=json.dumps(vehiculo_anterior.to_dict(), default=str),
            datos_nuevos=None 
        )
        return True
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error en eliminar_vehiculo_controller: {e}")
        raise Exception(f"Error interno al eliminar vehículo: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()