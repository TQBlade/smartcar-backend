# core/security.py

import hashlib
import jwt
import datetime

# 🚨 CAMBIA ESTO por una llave secreta larga y aleatoria.
# Puedes generar una con: python -c 'import os; print(os.urandom(24).hex())'
JWT_SECRET_KEY = "tu-llave-secreta-muy-larga-y-segura-aqui"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30


def hash_password(password: str) -> str:
    """
    Convierte una contraseña en un hash SHA256.
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(stored_hash: str, provided_password: str) -> bool:
    """
    Verifica si la contraseña proporcionada coincide con el hash almacenado.
    """
    return stored_hash == hash_password(provided_password)


def create_jwt_token(user_data: dict) -> str:
    """
    Crea un nuevo token JWT para la sesión del usuario.
    """
    try:
        payload = {
            "sub": user_data,  # El 'subject' de nuestro token (datos del usuario)
            "iat": datetime.datetime.utcnow(),  # Issued at time (cuándo se creó)
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRATION_MINUTES)
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token

    except Exception as e:
        print(f"Error al crear el token: {e}")
        return None

def validate_jwt_token(token: str) -> dict:
    """
    Valida un token JWT. Devuelve los datos (payload) si es válido, o None si no.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload['sub']
    except jwt.ExpiredSignatureError:
        print("Token ha expirado")
        return None
    except jwt.InvalidTokenError:
        print("Token inválido")
        return None
    
    #necesito editar este archivo