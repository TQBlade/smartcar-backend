import cv2
import easyocr
import numpy as np
import base64
import os
import re
from collections import Counter

# ==============================================================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==============================================================================
print("🚀 Inicializando Motor de Reconocimiento de Placas (v3.0 - Ultimate)...")
try:
    # Cargamos español (es) e inglés (en) para maximizar cobertura de caracteres
    reader = easyocr.Reader(['es', 'en'], gpu=False)
    print("✅ Motor OCR cargado correctamente.")
except Exception as e:
    print(f"❌ Error crítico cargando OCR: {e}")
    reader = None

# ==============================================================================
# 2. BASES DE CONOCIMIENTO (Diccionarios de Corrección)
# ==============================================================================

# Mapa: Cuando esperamos un NÚMERO (N) pero el OCR leyó una LETRA
L2N = {
    'O': '0', 'Q': '0', 'D': '0', 'U': '0', 'C': '0',
    'I': '1', 'J': '1', 'L': '1', 'T': '1', 'l': '1',
    'Z': '2', 'z': '2', '?': '2',
    'E': '3', 'B': '3',
    'A': '4',
    'S': '5', 's': '5',
    'G': '6', 'b': '6',
    'T': '7', 'Y': '7',
    'B': '8', 'R': '8',
    'g': '9', 'q': '9', 'P': '9'
}

# Mapa: Cuando esperamos una LETRA (L) pero el OCR leyó un NÚMERO
N2L = {
    '0': 'O',
    '1': 'I',
    '2': 'Z',
    '3': 'E',
    '4': 'A',
    '5': 'S',
    '6': 'G',
    '7': 'T',
    '8': 'B'
}

# Moldes oficiales
PATRONES = {
    'COL_CARRO': {'len': 6, 'mask': 'LLLNNN', 'regex': r'^[A-Z]{3}[0-9]{3}$'},
    'COL_MOTO':  {'len': 6, 'mask': 'LLLNNL', 'regex': r'^[A-Z]{3}[0-9]{2}[A-Z]$'},
    'VEN_AUTO':  {'len': 7, 'mask': 'LLNNNLL', 'regex': r'^[A-Z]{2}[0-9]{3}[A-Z]{2}$'},
    # 'VEN_OLD': {'len': 6, 'mask': 'LLLNNL', 'regex': r'^[A-Z]{3}[0-9]{2}[A-Z]$'} # Igual a moto COL
}

# Palabras a ignorar (Ruido común en los marcos de placas)
BLACKLIST = ['COLOMBIA', 'BOGOTA', 'MEDELLIN', 'ANTIGUO', 'AUTO', 'MOVIL', 'TRANSITO', 'SERVICIO', 'PARTICULAR', 'ENVIGADO', 'SABANETA']

# ==============================================================================
# 3. MOTOR DE PREPROCESAMIENTO DE IMÁGENES
# ==============================================================================
def generar_pipelines_imagen(img_original):
    """
    Genera múltiples versiones de la imagen para intentar vencer
    diferentes condiciones de luz, sombra y suciedad.
    """
    pipelines = []
    
    # --- A. Escala de Grises (Base) ---
    gray = cv2.cvtColor(img_original, cv2.COLOR_BGR2GRAY)
    pipelines.append(('GRAY', gray))

    # --- B. CLAHE (Para sombras fuertes como en la moto amarilla) ---
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray_clahe = clahe.apply(gray)
    pipelines.append(('CLAHE', gray_clahe))

    # --- C. Binarización Otsu (Alto contraste blanco/negro) ---
    # Bueno para placas sucias pero con buen contraste de tinta
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pipelines.append(('OTSU', otsu))

    # --- D. Aumento de Contraste Lineal (Para placas descoloridas) ---
    # alpha=1.5 (contraste), beta=0 (brillo)
    contrast = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
    pipelines.append(('CONTRAST', contrast))

    # --- E. Invertido (Para casos raros de letras claras fondo oscuro) ---
    # inverted = cv2.bitwise_not(otsu)
    # pipelines.append(('INVERT', inverted))

    return pipelines

# ==============================================================================
# 4. MOTOR DE ANÁLISIS Y CORRECCIÓN
# ==============================================================================
def aplicar_mascara(texto, mascara):
    """
    Intenta forzar un texto a cumplir una máscara específica (ej: LLLNNN).
    Retorna: (Texto Corregido, Penalización)
    Penalización: 0 = Perfecto, >0 = Se tuvieron que cambiar caracteres.
    Retorna (None, 999) si es imposible corregir.
    """
    texto_lista = list(texto)
    if len(texto_lista) != len(mascara): return None, 999
    
    penalizacion = 0
    nuevo_texto = []

    for i, tipo_esperado in enumerate(mascara):
        char = texto_lista[i]
        
        # 1. Si esperamos NÚMERO
        if tipo_esperado == 'N':
            if char.isdigit():
                nuevo_texto.append(char) # OK
            elif char in L2N:
                nuevo_texto.append(L2N[char]) # Corregido
                penalizacion += 1
            else:
                return None, 999 # Error fatal (ej: 'K' donde va número)

        # 2. Si esperamos LETRA
        elif tipo_esperado == 'L':
            if char.isalpha():
                nuevo_texto.append(char) # OK
            elif char in N2L:
                nuevo_texto.append(N2L[char]) # Corregido
                penalizacion += 1
            else:
                return None, 999 # Error fatal

    return "".join(nuevo_texto), penalizacion

def evaluar_candidato(texto_crudo):
    """
    Recibe un texto crudo del OCR (ej: "OMG-65O") y lo evalúa contra
    TODOS los patrones posibles. Devuelve el mejor ajuste.
    """
    # 1. Limpieza inicial: Solo alfanuméricos mayúsculas
    limpio = re.sub(r'[^A-Z0-9]', '', texto_crudo.upper())
    
    mejores_opciones = []

    # Generamos subcadenas para eliminar bordes (ventanas deslizantes)
    # Ej: "|OMG650" (7 chars) -> probamos "OMG650"
    subcadenas = [limpio]
    if len(limpio) > 6:
        for i in range(len(limpio) - 5): # Ventanas de 6
            subcadenas.append(limpio[i:i+6])
        for i in range(len(limpio) - 6): # Ventanas de 7
            subcadenas.append(limpio[i:i+7])

    # Probamos cada subcadena contra cada patrón
    for sub in subcadenas:
        largo = len(sub)
        
        for nombre_patron, reglas in PATRONES.items():
            if largo == reglas['len']:
                texto_corregido, costo = aplicar_mascara(sub, reglas['mask'])
                
                if texto_corregido:
                    # Cálculo de Puntaje (Score)
                    # Base 100. Restamos 10 por cada corrección.
                    score = 100 - (costo * 10)
                    
                    # Bonus por Regex exacto (Doble verificación)
                    if re.match(reglas['regex'], texto_corregido):
                        score += 5
                    
                    mejores_opciones.append({
                        'placa': texto_corregido,
                        'score': score,
                        'patron': nombre_patron,
                        'original': texto_crudo
                    })

    if not mejores_opciones:
        return None

    # Ordenamos por puntaje descendente
    mejores_opciones.sort(key=lambda x: x['score'], reverse=True)
    return mejores_opciones[0] # Retornamos el ganador

# ==============================================================================
# 5. FUNCIÓN PRINCIPAL EXPORTADA
# ==============================================================================
def detectar_placa(base64_image_data: str) -> str | None:
    if reader is None: return None

    try:
        # A. Decodificar Imagen
        if ',' in base64_image_data:
            base64_image_data = base64_image_data.split(',')[1]
        img_bytes = base64.b64decode(base64_image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None: return None

        # B. Generar Pipelines de Imagen
        imagenes_proc = generar_pipelines_imagen(img)
        
        todos_los_candidatos = []

        print(f"👁️  Analizando imagen con {len(imagenes_proc)} filtros...")

        # C. Barrido OCR
        for nombre_filtro, img_p in imagenes_proc:
            # allowlist: Solo caracteres que pueden estar en una placa
            resultados = reader.readtext(img_p, detail=0, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
            
            for txt in resultados:
                txt = txt.upper()
                # Filtrar basura obvia (palabras prohibidas o muy cortas)
                if len(txt) < 5 or any(b in txt for b in BLACKLIST):
                    continue
                
                # Evaluar candidato
                ganador_local = evaluar_candidato(txt)
                if ganador_local:
                    ganador_local['filtro'] = nombre_filtro
                    todos_los_candidatos.append(ganador_local)
                    # print(f"   > Candidato ({nombre_filtro}): {ganador_local['placa']} (Score: {ganador_local['score']})")

        # D. Selección del Ganador Absoluto
        if not todos_los_candidatos:
            print("⚠️ No se encontró ninguna placa válida.")
            return None

        # Ordenar por Score
        todos_los_candidatos.sort(key=lambda x: x['score'], reverse=True)
        ganador_absoluto = todos_los_candidatos[0]

        print(f"✅ PLACA DETECTADA: {ganador_absoluto['placa']} (Patrón: {ganador_absoluto['patron']}, Score: {ganador_absoluto['score']})")
        return ganador_absoluto['placa']

    except Exception as e:
        print(f"❌ Error en proceso OCR: {e}")
        return None

# --- TEST LOCAL ---
if __name__ == "__main__":
    # Cambia esto por la ruta de tu imagen local para probar
    path = os.path.join(os.path.dirname(__file__), "img_placas/placa_prueba3.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        detectar_placa(b64)
    else:
        print("Archivo de prueba no encontrado.")