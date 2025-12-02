import cv2
import easyocr
import numpy as np
import base64
import os
import re
import gc # Garbage Collector para limpiar RAM

# ==============================================================================
# 1. INICIALIZACIÓN (MODO AHORRO DE MEMORIA)
# ==============================================================================
print("🚀 Inicializando OCR (Modo Low-RAM)...")
try:
    # quantize=True reduce el uso de memoria del modelo a la mitad
    reader = easyocr.Reader(['es'], gpu=False, quantize=True)
    print("✅ Motor OCR cargado.")
except Exception as e:
    print(f"❌ Error OCR: {e}")
    reader = None

# ==============================================================================
# 2. DICCIONARIOS DE CORRECCIÓN
# ==============================================================================
L2N = {'O':'0','Q':'0','D':'0','U':'0','C':'0','I':'1','J':'1','L':'1','T':'1','l':'1','Z':'2','z':'2','?':'2','E':'3','B':'3','A':'4','S':'5','s':'5','G':'6','b':'6','B':'8','R':'8','g':'9','q':'9','P':'9'}
N2L = {'0':'O','1':'I','2':'Z','3':'E','4':'A','5':'S','6':'G','7':'T','8':'B'}

PATRONES = {
    'COL_CARRO': {'len': 6, 'mask': 'LLLNNN', 'regex': r'^[A-Z]{3}[0-9]{3}$'},
    'COL_MOTO':  {'len': 6, 'mask': 'LLLNNL', 'regex': r'^[A-Z]{3}[0-9]{2}[A-Z]$'},
    'VEN_AUTO':  {'len': 7, 'mask': 'LLNNNLL', 'regex': r'^[A-Z]{2}[0-9]{3}[A-Z]{2}$'}
}
BLACKLIST = ['COLOMBIA', 'BOGOTA', 'MEDELLIN', 'ANTIGUO', 'AUTO', 'MOVIL']

# ==============================================================================
# 3. LÓGICA DE CORRECCIÓN
# ==============================================================================
def aplicar_mascara(texto, mascara):
    texto_lista = list(texto)
    if len(texto_lista) != len(mascara): return None, 999
    costo = 0
    nuevo_texto = []
    for i, tipo_esperado in enumerate(mascara):
        char = texto_lista[i]
        if tipo_esperado == 'N':
            if char.isdigit(): nuevo_texto.append(char)
            elif char in L2N: 
                nuevo_texto.append(L2N[char])
                costo += 1
            else: return None, 999
        elif tipo_esperado == 'L':
            if char.isalpha(): nuevo_texto.append(char)
            elif char in N2L: 
                nuevo_texto.append(N2L[char])
                costo += 1
            else: return None, 999
    return "".join(nuevo_texto), costo

def evaluar_candidato(texto_crudo):
    limpio = re.sub(r'[^A-Z0-9]', '', texto_crudo.upper())
    largo = len(limpio)
    candidatos = []
    subcadenas = [limpio]
    if largo > 6:
        subcadenas.append(limpio[0:6])
        subcadenas.append(limpio[1:7])

    for sub in subcadenas:
        largo_sub = len(sub)
        for nombre, reglas in PATRONES.items():
            if largo_sub == reglas['len']:
                res, costo = aplicar_mascara(sub, reglas['mask'])
                if res:
                    score = 100 - (costo * 15)
                    if re.match(reglas['regex'], res): score += 10
                    candidatos.append({'placa': res, 'score': score, 'patron': nombre})
    
    if not candidatos: return None
    candidatos.sort(key=lambda x: x['score'], reverse=True)
    return candidatos[0]

# ==============================================================================
# 4. FUNCIÓN PRINCIPAL (OPTIMIZADA PARA MEMORIA)
# ==============================================================================
def detectar_placa(base64_image_data: str) -> str | None:
    if reader is None: return None

    try:
        # 1. Decodificar
        if ',' in base64_image_data: base64_image_data = base64_image_data.split(',')[1]
        img_bytes = base64.b64decode(base64_image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None: return None

        mejores_placas = []

        # --- ESTRATEGIA SECUENCIAL (AHORRO RAM) ---
        # Procesamos 1 filtro, leemos, y borramos la imagen de memoria inmediatamente.
        
        # FILTRO 1: GRISES (El más liviano)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        textos = reader.readtext(gray, detail=0, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        for t in textos:
            c = evaluar_candidato(t)
            if c: mejores_placas.append(c)
        
        # Limpieza RAM inmediata
        del textos
        gc.collect() 

        # Si ya encontramos algo con puntaje perfecto, retornamos y NO procesamos más (Ahorro máximo)
        if mejores_placas and mejores_placas[0]['score'] >= 100:
            print(f"✅ Placa rápida encontrada: {mejores_placas[0]['placa']}")
            return mejores_placas[0]['placa']

        # FILTRO 2: CLAHE (Para sombras, solo si no encontramos una perfecta antes)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray_clahe = clahe.apply(gray)
        textos = reader.readtext(gray_clahe, detail=0, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        for t in textos:
            c = evaluar_candidato(t)
            if c: mejores_placas.append(c)
        
        # Limpieza RAM
        del gray_clahe, clahe, textos
        gc.collect()

        # FILTRO 3: BINARIZACIÓN (Solo si seguimos dudando)
        # Blur suave para reducir ruido antes de binarizar
        blur = cv2.GaussianBlur(gray, (5,5), 0)
        _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        textos = reader.readtext(binary, detail=0, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        for t in textos:
            c = evaluar_candidato(t)
            if c: mejores_placas.append(c)

        # Limpieza Final
        del gray, blur, binary, textos, img, np_arr, img_bytes
        gc.collect()

        if mejores_placas:
            mejores_placas.sort(key=lambda x: x['score'], reverse=True)
            print(f"✅ Ganador final: {mejores_placas[0]['placa']}")
            return mejores_placas[0]['placa']

        return None

    except Exception as e:
        print(f"❌ Error memoria/OCR: {e}")
        return None