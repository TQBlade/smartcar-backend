# backend/models/vehiculo.py
from backend.core.db.connection import get_connection
import json

class Vehiculo:
    def __init__(self, id_vehiculo, placa, tipo, color, id_persona):
        """
        Clase que representa un Vehículo.
        """
        self.id_vehiculo = id_vehiculo
        self.placa = placa.upper()
        self.tipo = tipo          # 'Automovil', 'Motocicleta'
        self.color = color
        self.id_persona = id_persona  # Clave foránea a Persona

    def to_dict(self):
        """
        Convierte el objeto en un diccionario para serialización (JSON).
        """
        return {
            "id_vehiculo": self.id_vehiculo,
            "placa": self.placa,
            "tipo": self.tipo,
            "color": self.color,
            "id_persona": self.id_persona
        }

    @staticmethod
    def from_dict(data):
        """
        Crea una instancia de Vehiculo desde un diccionario (útil para POST/PUT).
        """
        return Vehiculo(
            id_vehiculo=data.get("id_vehiculo"),
            placa=data.get("placa", "").upper(),
            tipo=data.get("tipo"),
            color=data.get("color"),
            id_persona=data.get("id_persona")
        )

# ==========================================================
# FUNCIÓN QUE TE FALTABA (Copia esto al final del archivo)
# ==========================================================
def registrar_vehiculo_invitado_db(placa):
    """
    Registra un vehículo automáticamente asignado a la persona genérica (ID 9999).
    Tipo: 'Invitado', Color: 'Sin especificar'.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        # ID 9999 es el usuario 'INVITADO EVENTO'
        sql = """
            INSERT INTO vehiculo (placa, tipo, color, id_persona)
            VALUES (%s, 'Invitado', 'Sin especificar', 9999)
            RETURNING id_vehiculo
        """
        cur.execute(sql, (placa.upper(),))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌ Error registrando vehículo invitado: {e}")
        return False
    finally:
        cur.close()
        conn.close()