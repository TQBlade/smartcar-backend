# backend/routes/vehiculos_routes.py
# Define los Endpoints (/api/vehiculos) usando un Blueprint de Flask.

from flask import Blueprint, request, jsonify
# Importamos la lógica del controlador (corregido)
from core.controller_vehiculos import (
    obtener_vehiculos_controller,
    crear_vehiculo_controller,
    actualizar_vehiculo_controller
)

# 1. Creamos el Blueprint
vehiculos_bp = Blueprint('vehiculos_bp', __name__)

# --- Definición de Rutas ---

# GET /api/vehiculos
@vehiculos_bp.route('/api/vehiculos', methods=['GET'])
def get_vehiculos():
    """
    Endpoint para OBTENER todos los vehículos (con datos del propietario).
    """
    try:
        vehiculos = obtener_vehiculos_controller()
        return jsonify(vehiculos), 200
        
    except Exception as e:
        print(f"Error en GET /api/vehiculos: {e}")
        return jsonify({"error": str(e)}), 500

# POST /api/vehiculos
@vehiculos_bp.route('/api/vehiculos', methods=['POST'])
def create_vehiculo():
    """
    Endpoint para CREAR un nuevo vehículo.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Cuerpo de la petición vacío"}), 400
            
        headers = request.headers
        
        nuevo_id = crear_vehiculo_controller(data, headers)
        
        return jsonify({"mensaje": "Vehículo creado exitosamente", "id_vehiculo": nuevo_id}), 201

    except ValueError as ve: # Errores de validación (token, propietario no existe)
        status_code = 401 if "Token" in str(ve) else 400
        return jsonify({"error": str(ve)}), status_code
    except Exception as e:
        print(f"Error en POST /api/vehiculos: {e}")
        return jsonify({"error": str(e)}), 500

# PUT /api/vehiculos/<int:id_vehiculo>
@vehiculos_bp.route('/api/vehiculos/<int:id_vehiculo>', methods=['PUT'])
def update_vehiculo(id_vehiculo):
    """
    Endpoint para ACTUALIZAR un vehículo existente.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Cuerpo de la petición vacío"}), 400

        headers = request.headers
        
        actualizar_vehiculo_controller(id_vehiculo, data, headers)
        
        return jsonify({"mensaje": "Vehículo actualizado exitosamente"}), 200
        
    except ValueError as ve:
        if "no encontrado" in str(ve):
            return jsonify({"error": str(ve)}), 404
        else: # Error de token, propietario no existe, etc.
            status_code = 401 if "Token" in str(ve) else 400
            return jsonify({"error": str(ve)}), status_code
    except Exception as e:
        print(f"Error en PUT /api/vehiculos/{id_vehiculo}: {e}")
        return jsonify({"error": str(e)}), 500