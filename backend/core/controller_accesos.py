# backend/core/controller_accesos.py

import json
from backend.core.db.connection import get_connection
from backend.models.acceso import (
    verificar_vehiculo_dentro, 
    registrar_salida_db, 
    registrar_entrada_db
)
from backend.ocr.detector import detectar_placa 
from backend.core.auditoria_utils import registrar_auditoria_global
from backend.core.controller_calendario import hay_evento_activo_controller
from backend.models.vehiculo import registrar_vehiculo_invitado_db

# ==========================================================
# 1. FUNCIÓN PARA OBTENER EL HISTORIAL CON FILTROS
# ==========================================================
def obtener_historial_accesos(filtros=None):
    """
    Obtiene el historial filtrado por placa, fechas y tipo de vehículo.
    """
    if filtros is None:
        filtros = {}

    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Consulta Base: Unimos con vehiculo para sacar el tipo y la placa
        sql = """
            SELECT 
                a.id_acceso,
                v.placa,
                TO_CHAR(a.fecha_hora, 'HH24:MI:SS') as entrada,
                TO_CHAR(a.hora_salida, 'HH24:MI:SS') as salida,
                TO_CHAR(a.fecha_hora, 'YYYY-MM-DD') as fecha,
                a.resultado,
                v.tipo 
            FROM acceso a
            JOIN vehiculo v ON a.id_vehiculo = v.id_vehiculo
            WHERE 1=1
        """
        
        params = []

        # --- FILTROS DINÁMICOS ---
        
        # 1. Filtro por Placa (búsqueda parcial)
        if filtros.get('placa'):
            sql += " AND v.placa ILIKE %s"
            params.append(f"%{filtros['placa']}%")
        
        # 2. Filtro por Tipo de Vehículo (exacto)
        if filtros.get('tipo'):
            sql += " AND v.tipo = %s"
            params.append(filtros['tipo'])

        # 3. Filtro Desde (Fecha)
        if filtros.get('desde'):
            sql += " AND DATE(a.fecha_hora) >= %s"
            params.append(filtros['desde'])

        # 4. Filtro Hasta (Fecha)
        if filtros.get('hasta'):
            sql += " AND DATE(a.fecha_hora) <= %s"
            params.append(filtros['hasta'])

        # Ordenar descendente (más reciente primero)
        sql += " ORDER BY a.fecha_hora DESC"

        cur.execute(sql, tuple(params))
        data = cur.fetchall()
        cur.close()
        conn.close()

        # Formateamos para JSON
        historial = []
        for row in data:
            historial.append({
                "id": row[0],
                "placa": row[1],
                "entrada": row[2],
                "salida": row[3] if row[3] else "--",
                "fecha": row[4],
                "estado": row[5],
                "tipo": row[6]
            })
        
        return historial

    except Exception as e:
        print(f"❌ Error obteniendo historial filtrado: {e}")
        return []

# ==========================================================
# 2. FUNCIÓN PARA PROCESAR VALIDACIÓN (OCR + LÓGICA + AUDITORÍA)
# ==========================================================
def procesar_validacion_acceso(data_request, vigilante_id):
    try:
        # 1. Decodificar
        data = json.loads(data_request)
        imagen_b64 = data.get("image_base64")
        tipo_acceso = data.get("tipo_acceso")

        if not imagen_b64:
            return {"error": "No hay imagen"}, 400

        # 2. OCR
        placa_detectada = detectar_placa(imagen_b64) 
        if not placa_detectada:
            return {"resultado": "Denegado", "datos": {"placa": "No detectada", "motivo": "Imagen ilegible"}}, 200

        print(f"📡 Procesando: Placa {placa_detectada} | Tipo: {tipo_acceso}")

        # 3. Lógica de Validación
        id_acceso_pendiente = verificar_vehiculo_dentro(placa_detectada)

        if tipo_acceso == 'salida':
            # --- SALIDA ---
            if not id_acceso_pendiente:
                return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": "El vehículo NO tiene entrada."}}, 200
            else:
                if registrar_salida_db(id_acceso_pendiente):
                    # Auditoría Salida
                    registrar_auditoria_global(id_usuario=vigilante_id, entidad="ACCESO", id_entidad=id_acceso_pendiente, accion="SALIDA_VEHICULO", datos_nuevos={"placa": placa_detectada, "resultado": "Salida Exitosa"})
                    return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "Salida Exitosa"}}, 200
                else:
                    return {"error": "Error DB"}, 500
        
        else: 
            # --- ENTRADA ---
            if id_acceso_pendiente:
                return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": "El vehículo YA está dentro."}}, 200
            
            else:
                # INTENTO 1: Registrar entrada normal
                res = registrar_entrada_db(placa_detectada, vigilante_id)
                
                if res['status'] == 'ok':
                    # Éxito normal (Vehículo registrado)
                    registrar_auditoria_global(id_usuario=vigilante_id, entidad="ACCESO", id_entidad=0, accion="ENTRADA_VEHICULO", datos_nuevos={"placa": placa_detectada, "resultado": "Entrada Exitosa"})
                    return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "Entrada Registrada"}}, 200
                
                else:
                    # FALLÓ: El vehículo no existe.
                    # --- NUEVA LÓGICA: EVENTOS / INVITADOS ---
                    
                    # Verificamos si hay evento activo
                    if hay_evento_activo_controller():
                        print(f"🎉 Evento activo detectado. Registrando invitado: {placa_detectada}")
                        
                        # Creamos el vehículo temporalmente
                        if registrar_vehiculo_invitado_db(placa_detectada):
                            
                            # Intentamos registrar la entrada de nuevo
                            res_invitado = registrar_entrada_db(placa_detectada, vigilante_id)
                            
                            if res_invitado['status'] == 'ok':
                                registrar_auditoria_global(id_usuario=vigilante_id, entidad="ACCESO", id_entidad=0, accion="ENTRADA_INVITADO", datos_nuevos={"placa": placa_detectada, "evento": "Acceso por Evento"})
                                return {"resultado": "Autorizado", "datos": {"placa": placa_detectada, "propietario": "INVITADO (Evento Activo)"}}, 200
                    
                    # Si no hay evento o falló el registro invitado, denegamos normal
                    return {"resultado": "Denegado", "datos": {"placa": placa_detectada, "motivo": "Vehículo no registrado y sin eventos activos"}}, 200

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}, 500