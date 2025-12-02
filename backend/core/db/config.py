import os
from dotenv import load_dotenv

# Carga las variables del archivo .env en el entorno
load_dotenv()

class Config:
    # Lee las variables del entorno.
    # Añadimos valores por defecto por si acaso, excepto para la contraseña.
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bd_carros")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD")