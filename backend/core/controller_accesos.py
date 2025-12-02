# backend/core/controller_accesos.py
import json
from core.db.connection import get_connection
from models.acceso import (
    verificar_vehiculo_dentro, 
    registrar_salida_db, 
    registrar_entrada_db
)
from ocr.detector import detectar_placa 
from core.auditoria_utils import registrar_auditoria_global

def obtener_historial_accesos(filtros=None):
    if filtros is None: filtros = {}
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = """
            SELECT 
                a.id_acceso, v.placa, TO_CHAR(a.fecha_hora, 'HH24:MI:SS') as entrada,
                TO_CHAR(a.hora_salida, 'HH24:MI:SS') as salida, TO_CHAR(a.fecha_hora, 'YYYY-MM-DD') as fecha,
                a.resultado, v.tipo 
            FROM acceso a JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo WHERE 1=1
        """
        params = []
        if filtros.get('placa'): sql += " AND v.placa ILIKE %s"; params.append(f"%{filtros['placa']}%")
        if filtros.get('tipo'): sql += " AND v.tipo = %s"; params.append(filtros['tipo'])
        if filtros.get('desde'): sql += " AND DATE(a.fecha_hora) >= %s"; params.append(filtros['desde'])
        if filtros.get('hasta'): sql += " AND DATE(a.fecha_hora) <= %s"; params.append(filtros['hasta'])
        sql += " ORDER BY a.fecha_hora DESC"
        cur.execute(sql, tuple(params))
        data = cur.fetchall()
        cur.close(); conn.close()
        historial = []
        for row in data:
            historial.append({
                "id": row[0], "placa": row[1], "entrada": row[2], "salida": row[3] if row[3] else "--",
                "fecha": row[4], "estado": row[5], "tipo": row[6]
            })
        return historial
    except Exception as e:
        print(f"❌ Error historial: {e}")
        return []

def procesar_validacion_acceso(data_input, vigilante_id):
    try:
        # CAMBIO CLAVE: Ya no hacemos json.loads() porque server.py envía un diccionario
        # Si por alguna razón llega como string (tests locales antiguos), intentamos parsear
        if isinstance(data_input, str) or isinstance(data_input, bytes):
            data = json.loads(data_input)
        else:
            data = data_input # Ya es diccionario

        imagen_b64 = data.get("image_base64")
        tipo_acceso = data.get("tipo_acceso") 

        if not imagen_b64: return {"error": "No hay imagen"}, 400

        placa_detectada = detectar_placa(imagen_b64) 
        
        if not placa_detectada:
            return {"resultado": "Denegado", "datos": {"placa": "No detectada", "motivo": "Imagen ilegible"}}, 200

        print(f"📡 Procesando: {placa_detectada} ({tipo_acceso})")

        # LOGICA NEGOCIO
        id_acceso_pendiente = verificar_vehiculo_dentro(placa_detectada)

        if tipo_acceso == 'salida':
            if not id_acceso_pendiente:
                return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": "No tiene entrada"}}, 200
            else:
                if registrar_salida_db(id_acceso_pendiente):
                    registrar_auditoria_global(vigilante_id, "ACCESO", id_acceso_pendiente, "SALIDA", datos_nuevos={"placa": placa_detectada})
                    return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "Salida Exitosa"}}, 200
                else:
                    return {"error": "Error DB"}, 500
        else: 
            if id_acceso_pendiente:
                return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": "Ya está dentro"}}, 200
            else:
                res = registrar_entrada_db(placa_detectada, vigilante_id)
                if res['status'] == 'ok':
                    registrar_auditoria_global(vigilante_id, "ACCESO", 0, "ENTRADA", datos_nuevos={"placa": placa_detectada})
                    return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "Entrada Registrada"}}, 200
                else:
                    # Si falla registro, intentar lógica de invitados (calendario)
                    from core.controller_calendario import hay_evento_activo_controller
                    from models.vehiculo import registrar_vehiculo_invitado_db
                    
                    if hay_evento_activo_controller():
                        if registrar_vehiculo_invitado_db(placa_detectada):
                            res_inv = registrar_entrada_db(placa_detectada, vigilante_id)
                            if res_inv['status'] == 'ok':
                                registrar_auditoria_global(vigilante_id, "ACCESO", 0, "INVITADO", datos_nuevos={"placa": placa_detectada})
                                return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "INVITADO EVENTO"}}, 200
                    
                    return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": res['mensaje']}}, 200

    except Exception as e:
        print(f"❌ Error controlador: {e}")
        return {"error": str(e)}, 500