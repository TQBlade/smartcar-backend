from flask import Blueprint, request, jsonify
import psycopg2 
import os
import jwt 
from datetime import datetime, timedelta

# Inicialización del Blueprint para manejar las rutas relacionadas con el login
login_bp = Blueprint('login', __name__)

# Configuración (DEBES AJUSTAR ESTO A TU ENTORNO)
DB_NAME = 'bd_carros'
DB_USER = 'postgres'
# VUELVE A PONER TU CONTRASEÑA REAL AQUÍ:
DB_PASSWORD = '123456' 
DB_HOST = 'localhost'
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'SUPER_SECRETO_Y_LARGO_2025') 

ROL_TO_NIVEL = {
    "Administrador": 1,
    "Vigilante": 0
}

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST
        )
        return conn
    except psycopg2.Error as e:
        # Imprime el error exacto de la conexión en la consola de Flask/servidor
        print(f"🚨 ERROR FATAL DE CONEXIÓN A POSTGRES: {e}") 
        return None

@login_bp.route("/login", methods=["POST"])
def login():
    """
    Ruta para manejar la solicitud de inicio de sesión.
    Valida credenciales y devuelve un JWT.
    """
    data = request.get_json()
    usuario = data.get('usuario')
    clave = data.get('clave')
    rol_str = data.get('rol') 

    if not all([usuario, clave, rol_str]):
        return jsonify({"error": "Faltan datos de usuario, clave o rol"}), 400

    nivel_requerido = ROL_TO_NIVEL.get(rol_str)
    if nivel_requerido is None:
         return jsonify({"error": "Rol seleccionado no válido"}), 400


    conn = get_db_connection()
    if conn is None:
        # El error de conexión ya se imprimió en get_db_connection
        return jsonify({"error": "Error interno. No se pudo conectar a la base de datos"}), 500
        
    cursor = conn.cursor()
    
    try:
        # Imprime la consulta y los valores en la consola para depuración
        print(f"DEBUG: Intentando autenticar usuario: {usuario} con nivel: {nivel_requerido}")
        
        cursor.execute(
            """
            SELECT nu, nombre, nivel 
            FROM tmusuarios 
            WHERE usuario = %s AND clave = %s AND nivel = %s
            """,
            (usuario, clave, nivel_requerido)
        )
        user_record = cursor.fetchone()

        if user_record:
            nu, nombre, nivel = user_record
            
            # [Generación de JWT y retorno de éxito, omitido para brevedad]
            token_payload = {
                'nu': nu,
                'nombre': nombre,
                'nivel': nivel,
                'exp': datetime.utcnow() + timedelta(hours=2)
            }
            token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm='HS256')

            return jsonify({
                "message": "Autenticación exitosa",
                "token": token,
                "user": {
                    "id": nu,
                    "nombre": nombre,
                    "nivel": nivel
                }
            }), 200
        else:
            # Si no se encuentra el registro, el error 401 es correcto
            print(f"DEBUG: Autenticación fallida para {usuario}.")
            return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    except psycopg2.Error as e:
        print(f"🚨 ERROR EN CONSULTA SQL (tmusuarios): {e}")
        return jsonify({"error": "Error interno del servidor al consultar credenciales"}), 500
    finally:
        cursor.close()
        conn.close()