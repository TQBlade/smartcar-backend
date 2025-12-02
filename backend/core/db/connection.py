import psycopg2
import os
from dotenv import load_dotenv

# Carga las variables del archivo .env en el entorno
load_dotenv()

def get_connection():
    try:
        # Llama a las variables de entorno para la conexión
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT"),
            client_encoding='UTF8'
        )
        
        # --- CORRECCIÓN DE HORA ---
        # Forzamos la sesión a la hora de Colombia inmediatamente al conectar
        cur = conn.cursor()
        cur.execute("SET TIME ZONE 'America/Bogota';")
        cur.close()
        conn.commit()
        # --------------------------
        
        return conn
    except Exception as e:
        print(f"❌ Error crítico conectando a la BD: {e}")
        return None