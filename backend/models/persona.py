# backend/models/persona.py
# Representación de la tabla 'persona' (alineada con bd_carros.sql)

class Persona:
    def __init__(self, id_persona, doc_identidad, nombre, tipo_persona, estado=1):
        """
        Clase que representa a una Persona (Estudiante, Docente, etc.).
        """
        self.id_persona = id_persona
        self.doc_identidad = doc_identidad
        self.nombre = nombre
        self.tipo_persona = tipo_persona  # 'ESTUDIANTE', 'DOCENTE', 'ADMINISTRATIVO'
        self.estado = estado              # 1 = Activo, 0 = Eliminado (según tmstatus)

    def to_dict(self):
        """
        Convierte el objeto en un diccionario para serialización (JSON).
        """
        return {
            "id_persona": self.id_persona,
            "doc_identidad": self.doc_identidad,
            "nombre": self.nombre,
            "tipo_persona": self.tipo_persona,
            "estado": self.estado
        }

    @staticmethod
    def from_dict(data):
        """
        Crea una instancia de Persona desde un diccionario (útil para POST/PUT).
        """
        return Persona(
            id_persona=data.get("id_persona"),
            doc_identidad=data.get("doc_identidad"),
            nombre=data.get("nombre"),
            tipo_persona=data.get("tipo_persona"),
            estado=data.get("estado", 1)
        )