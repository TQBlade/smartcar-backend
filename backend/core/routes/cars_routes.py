from flask import Blueprint, jsonify
from db.connection import get_connection

cars_bp = Blueprint('cars', __name__)

@cars_bp.route('/carros', methods=['GET'])
def get_carros():
    conn = get_connection()
    if conn is None:
        return jsonify({"error": "No se pudo conectar a la base de datos"}), 500

    cur = conn.cursor()
    cur.execute("SELECT * FROM carros;")
    data = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify(data)
