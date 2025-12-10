# backend/core/pico_placa.py
from datetime import datetime

def verificar_pico_placa(placa):
    """
    Lógica de Pico y Placa para CÚCUTA.
    Regla General:
    - Lunes: 1 y 2
    - Martes: 3 y 4
    - Miércoles: 5 y 6
    - Jueves: 7 y 8
    - Viernes: 9 y 0
    - Horario: 7:00 AM a 7:00 PM (Continuo)
    """
    if not placa or len(placa) < 6:
        return {"restriccion": False, "mensaje": "Placa inválida"}

    # Obtener último dígito (si es moto y termina en letra, tomamos el número anterior)
    ultimo_caracter = placa[-1]
    if ultimo_caracter.isdigit():
        ultimo_digito = int(ultimo_caracter)
    else:
        # Caso Moto (ej: AAA12B -> tomamos el 2)
        try:
            ultimo_digito = int(placa[-2])
        except:
            return {"restriccion": False, "mensaje": "Formato de placa no reconocido"}
    
    ahora = datetime.now()
    dia_semana = ahora.weekday() # 0=Lun, 1=Mar, ... 6=Dom
    hora_actual = ahora.hour

    # 1. Fines de semana libres
    if dia_semana >= 5:
        return {"restriccion": False, "mensaje": "Fin de semana: Libre circulación"}

    # 2. Reglas Cúcuta (Dígitos)
    reglas = {
        0: [1, 2], # Lunes
        1: [3, 4], # Martes
        2: [5, 6], # Miércoles
        3: [7, 8], # Jueves
        4: [9, 0]  # Viernes
    }

    digitos_hoy = reglas.get(dia_semana, [])

    # 3. Validar Dígito
    if ultimo_digito not in digitos_hoy:
        return {"restriccion": False, "mensaje": f"Hoy NO aplica para terminados en {ultimo_digito}"}

    # 4. Validar Horario (7am a 7pm)
    en_horario = (7 <= hora_actual < 19)

    if en_horario:
        return {"restriccion": True, "mensaje": f"🚫 PICO Y PLACA ACTIVO CÚCUTA (7am - 7pm)"}
    else:
        return {"restriccion": False, "mensaje": f"⚠️ Tu placa tiene restricción hoy, pero NO a esta hora."}