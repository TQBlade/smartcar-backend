# ===========================================================
#  SmartCar - Servidor Principal (PRODUCCIÓN / NUBE)
# ===========================================================
import sys
import os
from flask import Flask, jsonify, request, render_template, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import jwt
from functools import wraps
from io import BytesIO
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Importaciones corregidas para la estructura plana en Render
from core.db.connection import get_connection
from models.user_model import verificar_usuario
from core.auditoria_utils import registrar_auditoria_global 

# Controladores
from core.controller_personas import (
    desactivar_persona_controller, obtener_personas_controller,
    crear_persona_controller, actualizar_persona_controller
)
from core.controller_vehiculos import (
    eliminar_vehiculo_controller, obtener_vehiculos_controller,
    crear_vehiculo_controller, actualizar_vehiculo_controller
)
from core.controller_accesos import (
    obtener_historial_accesos, procesar_validacion_acceso
)
from core.controller_calendario import (
    obtener_eventos_controller, crear_evento_controller,
    actualizar_evento_controller, eliminar_evento_controller,
    verificar_evento_controller
)
from core.controller_incidencias import (
    obtener_vehiculos_en_patio, crear_incidente_manual,
    obtener_estado_actual_patio, crear_novedad_general,       
    obtener_historial_vigilante  
)
from core.controller_alertas import (
    obtener_alertas_controller, eliminar_alerta_controller
)
from models.auditoria import obtener_historial_auditoria
from models.dashboard_model import (
    obtener_ultimos_accesos, contar_total_vehiculos,
    contar_alertas_activas, buscar_placa_bd,
    obtener_ocupacion_real
)
from models.admin_model import (
    obtener_datos_dashboard,
    obtener_accesos_detalle,
    registrar_vigilante_completo, 
    obtener_todos_vigilantes,     
    obtener_data_reporte_completo,
    actualizar_vigilante_completo,
    eliminar_vigilante_completo
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "frontend", "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# --- CONFIGURACIÓN CORS PARA PRODUCCIÓN ---
# Esto permite que Vercel (o cualquier dominio) consuma tu API sin errores.
CORS(app, resources={r"/*": {"origins": "*"}})

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "SmartCar_SeguridadUltra_2025")

def token_requerido(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token: return jsonify({"error": "Token no proporcionado"}), 401
        try:
            token = token.replace("Bearer ", "")
            datos = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.usuario_actual = datos
        except: return jsonify({"error": "Token inválido/expirado"}), 401
        return f(*args, **kwargs)
    return decorador

@app.route("/")
def index(): return "SmartCar API is Running on Cloud 🚀"

@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        user = verificar_usuario(data.get("usuario"), data.get("clave"), data.get("rol"))
        if not user: return jsonify({"error": "Credenciales inválidas"}), 401

        token = jwt.encode({
            "usuario": user["usuario"], "rol": user["rol"],
            "id_audit": user["id_audit"], 
            "exp": datetime.utcnow() + timedelta(hours=8)
        }, app.config["SECRET_KEY"], algorithm="HS256")
        
        registrar_auditoria_global(user["id_audit"], "SISTEMA", 0, "INICIO_SESION", None, {"usuario": user["usuario"]})

        return jsonify({"status": "ok", "token": token, "user": user}), 200
    except Exception as e: return jsonify({"error": str(e)}), 500

# RUTAS DASHBOARD VIGILANTE
@app.route("/api/ocupacion", methods=["GET"])
def api_ocupacion(): return jsonify(obtener_ocupacion_real())

@app.route("/api/ultimos_accesos", methods=["GET"])
def api_ultimos_accesos(): return jsonify(obtener_ultimos_accesos())

@app.route("/api/total_vehiculos", methods=["GET"])
def api_total_vehiculos(): return jsonify(contar_total_vehiculos())

@app.route("/api/alertas_activas", methods=["GET"])
def api_alertas_activas(): return jsonify(contar_alertas_activas())

@app.route("/api/buscar_placa/<placa>", methods=["GET"])
def api_buscar_placa(placa):
    data = buscar_placa_bd(placa)
    return jsonify(data) if data else (jsonify({"error": "No encontrada"}), 404)

# RUTAS DASHBOARD ADMIN
@app.route("/api/admin/resumen", methods=["GET"])
@token_requerido
def api_admin_resumen(): return jsonify(obtener_datos_dashboard())

@app.route("/api/admin/accesos", methods=["GET"])
@token_requerido
def api_admin_accesos(): return jsonify(obtener_accesos_detalle())

@app.route("/api/admin/auditoria", methods=["GET"])
@token_requerido
def api_admin_auditoria(): return jsonify(obtener_historial_auditoria()), 200

# GESTIÓN VIGILANTES
@app.route("/api/admin/vigilantes", methods=["GET"])
@token_requerido
def list_vigilantes(): return jsonify(obtener_todos_vigilantes()), 200

@app.route("/api/admin/registrar_vigilante", methods=["POST"])
@token_requerido
def api_registrar_vigilante():
    if registrar_vigilante_completo(request.get_json(), request.usuario_actual['id_audit']):
        return jsonify({"mensaje": "Registrado"}), 201
    return jsonify({"error": "Error al registrar"}), 500

@app.route("/api/admin/vigilantes/<int:id>", methods=["PUT"])
@token_requerido
def update_vigilante_api(id):
    if actualizar_vigilante_completo(id, request.get_json(), request.usuario_actual['id_audit']):
        return jsonify({"mensaje": "Actualizado"}), 200
    return jsonify({"error": "Error"}), 500

@app.route("/api/admin/vigilantes/<int:id>", methods=["DELETE"])
@token_requerido
def delete_vigilante_api(id):
    if eliminar_vigilante_completo(id, request.usuario_actual['id_audit']):
        return jsonify({"mensaje": "Eliminado"}), 200
    return jsonify({"error": "Error"}), 500

# REPORTES
@app.route("/api/admin/exportar/excel", methods=["GET"])
@token_requerido
def exportar_excel():
    fi, ff = request.args.get('inicio'), request.args.get('fin')
    reporte = obtener_data_reporte_completo(fi, ff)
    if not reporte: return jsonify({"error": "Error"}), 500
    wb = Workbook()
    ws = wb.active; ws.append(["Reporte General", f"{fi} a {ff}"])
    buffer = BytesIO(); wb.save(buffer); buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Reporte.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# CRUD PERSONAS
@app.route("/api/personas", methods=["GET", "POST"])
@token_requerido
def handle_personas():
    if request.method == 'GET': return jsonify(obtener_personas_controller()), 200
    id_n = crear_persona_controller(request.json, request.usuario_actual)
    return jsonify({"mensaje": "Creado", "id": id_n}), 201

@app.route("/api/personas/<int:id_p>", methods=["PUT", "DELETE"])
@token_requerido
def handle_persona_id(id_p):
    if request.method == 'PUT':
        actualizar_persona_controller(id_p, request.json, request.usuario_actual)
        return jsonify({"mensaje": "OK"}), 200
    desactivar_persona_controller(id_p, request.usuario_actual)
    return jsonify({"mensaje": "OK"}), 200

# CRUD VEHÍCULOS
@app.route("/api/vehiculos", methods=["GET", "POST"])
@token_requerido
def handle_vehiculos():
    if request.method == 'GET': return jsonify(obtener_vehiculos_controller()), 200
    id_n = crear_vehiculo_controller(request.json, request.usuario_actual)
    return jsonify({"mensaje": "Creado", "id": id_n}), 201

@app.route("/api/vehiculos/<int:id_v>", methods=["PUT", "DELETE"])
@token_requerido
def handle_vehiculo_id(id_v):
    if request.method == 'PUT':
        actualizar_vehiculo_controller(id_v, request.json, request.usuario_actual)
        return jsonify({"mensaje": "OK"}), 200
    eliminar_vehiculo_controller(id_v, request.usuario_actual)
    return jsonify({"mensaje": "OK"}), 200

# USUARIO
@app.route("/api/usuario", methods=["GET"])
@token_requerido
def obtener_usuario(): return jsonify({"status": "ok", "user": request.usuario_actual}), 200

# ACCESOS Y OPERACIÓN
@app.route("/api/accesos", methods=["GET"])
@token_requerido
def get_historial_accesos():
    filtros = { k: request.args.get(k) for k in ['placa', 'tipo', 'desde', 'hasta'] }
    return jsonify(obtener_historial_accesos(filtros)), 200

@app.route("/api/accesos/validar", methods=["POST"])
def validar_acceso_ocr():
    res, st = procesar_validacion_acceso(request.data, 1)
    return jsonify(res), st

@app.route("/api/admin/alertas", methods=["GET"])
@token_requerido
def get_alertas(): return jsonify(obtener_alertas_controller()), 200

@app.route("/api/admin/alertas/<int:id_a>", methods=["DELETE"])
@token_requerido
def delete_alerta(id_a):
    if eliminar_alerta_controller(id_a, request.usuario_actual, request.get_json().get('accion_resolucion', 'General')):
        return jsonify({"mensaje": "OK"}), 200
    return jsonify({"error": "Error"}), 500

@app.route("/api/vigilante/estado-patio", methods=["GET"])
@token_requerido
def get_estado_patio(): return jsonify(obtener_estado_actual_patio()), 200

@app.route("/api/vigilante/novedad", methods=["POST"])
@token_requerido
def post_novedad():
    if crear_novedad_general(request.get_json(), request.usuario_actual['id_audit']): return jsonify({"mensaje": "OK"}), 201
    return jsonify({"error": "Error"}), 500

@app.route("/api/vigilante/mis-reportes", methods=["GET"])
@token_requerido
def get_mis_reportes(): return jsonify(obtener_historial_vigilante(request.usuario_actual['id_audit'])), 200

@app.route("/api/vigilante/vehiculos-en-patio", methods=["GET"])
@token_requerido
def get_vehiculos_patio(): return jsonify(obtener_vehiculos_en_patio()), 200

@app.route("/api/vigilante/reportar", methods=["POST"])
@token_requerido
def post_reportar_incidente():
    if crear_incidente_manual(request.get_json(), request.usuario_actual['id_audit']): return jsonify({"mensaje": "OK"}), 201
    return jsonify({"error": "Error"}), 500

# CALENDARIO
@app.route("/api/eventos", methods=["GET", "POST"])
@token_requerido
def handle_eventos():
    if request.method == 'GET': return jsonify(obtener_eventos_controller()), 200
    id_n = crear_evento_controller(request.get_json(), request.usuario_actual)
    return jsonify({"mensaje": "OK", "id": id_n}), 201

@app.route("/api/eventos/<int:id_e>", methods=["PUT", "DELETE"])
@token_requerido
def handle_evento_id(id_e):
    if request.method == 'PUT':
        actualizar_evento_controller(id_e, request.get_json())
        return jsonify({"mensaje": "OK"}), 200
    eliminar_evento_controller(id_e, request.usuario_actual)
    return jsonify({"mensaje": "OK"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))