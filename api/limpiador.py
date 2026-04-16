from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error

def limpiar_informe_medico(texto_sucio):
    """
    Función de limpieza que extrae datos clave del texto bruto para enviarlos a la IA.
    """
    resultado = {
        "fecha_informe": "",
        "historial_clinico": [],
        "medicacion": [],
        "analitica": []
    }

    # 1. Extraer fecha general
    match_fecha = re.search(r'Fecha:\s*(\d{1,2}/\d{1,2}/\d{4},\s*\d{2}:\d{2}:\d{2})', texto_sucio)
    if match_fecha:
        resultado["fecha_informe"] = match_fecha.group(1)

    # 2. SECCIÓN 1: HISTORIAL CLÍNICO
    if "=== SECCIÓN 1: HISTORIAL CLÍNICO ===" in texto_sucio:
        sec_hist = texto_sucio.split("=== SECCIÓN 1:")[1].split("=== SECCIÓN 2:")[0]
        lineas_hist = [l.strip() for l in sec_hist.split('\n') if l.strip()]
        for i, linea in enumerate(lineas_hist):
            if re.match(r'^\d{2}/\d{2}/\d{4}', linea):
                if i + 1 < len(lineas_hist):
                    diagnostico = lineas_hist[i+1]
                    if not diagnostico.startswith("("): 
                        resultado["historial_clinico"].append({"Fecha": linea, "Diagnostico": diagnostico})

    # 3. SECCIÓN 2: MEDICACIÓN ACTIVA
    if "=== SECCIÓN 2: MEDICACIÓN ACTIVA ===" in texto_sucio:
        sec_med = texto_sucio.split("=== SECCIÓN 2: MEDICACIÓN ACTIVA ===")[1].split("=== SECCIÓN 3:")[0]
        lineas_med = [l.strip() for l in sec_med.split('\n') if l.strip() and l != "FECHA\tMEDICAMENTO"]
        i = 0
        while i < len(lineas_med):
            linea = lineas_med[i]
            if any(k in linea for k in ["MG", "AMP", "SOL", "ML", "UI"]):
                partes = linea.split('\t')
                farmaco = partes[0].strip()
                dosis = partes[1].strip() if len(partes) > 1 else ""
                resultado["medicacion"].append({
                    "Farmaco": farmaco, "Dosis": dosis,
                    "Unidad": lineas_med[i+1] if i+1 < len(lineas_med) else "",
                    "Frecuencia": lineas_med[i+2] if i+2 < len(lineas_med) else ""
                })
                i += 3
            else: i += 1

    # 4. SECCIÓN 3: ANALÍTICA
    if "=== SECCIÓN 3: ANALÍTICA ===" in texto_sucio:
        sec_ana = texto_sucio.split("=== SECCIÓN 3: ANALÍTICA ===")[1]
        lineas_ana = [l.strip() for l in sec_ana.split('\n') if l.strip()]
        ruido = ["BIOQUIMICA GENERAL", "HEMATIMETRIA", "HEMOSTASIA", "Procedencia", "HELL - URGENCIAS", "URL:"]
        prueba_actual = None
        for linea in lineas_ana:
            if any(r in linea for r in ruido) or linea.startswith("http") or re.match(r'^Fecha:', linea): continue
            if ":" in linea:
                if prueba_actual: resultado["analitica"].append(prueba_actual)
                prueba_actual = {"Prueba": linea.split(":")[0].strip(), "Valor": "", "Rango": "", "Unidad": ""}
            elif re.match(r'^[><]?\d+([,.]\d+)?$', linea) and prueba_actual:
                prueba_actual["Valor"] = linea
            elif re.match(r'^[\d,.]+\s*-\s*[\d,.]+$', linea) and prueba_actual:
                prueba_actual["Rango"] = linea
            elif prueba_actual and len(linea) < 15 and not re.match(r'^[><]?\d', linea):
                prueba_actual["Unidad"] = linea
        if prueba_actual: resultado["analitica"].append(prueba_actual)

    return resultado

def consultar_groq(datos_limpios, api_key):
    """
    Motor de Inteligencia Artificial con reglas de veracidad médica estrictas.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Prompt optimizado para evitar alucinaciones y seguir tus plantillas
    prompt_maestro = f"""
    Actúa como un médico Anestesiólogo experto en medicina preoperatoria. 
    Tu objetivo es transcribir y organizar información REAL. Está TERMINANTEMENTE PROHIBIDO inventar datos.

    ### DATOS DE ENTRADA (JSON):
    {json.dumps(datos_limpios, ensure_ascii=False)}

    ### INSTRUCCIONES DE SEGURIDAD:
    1. SINCERIDAD ABSOLUTA: Si un dato (Edad, Peso, Hb, etc.) no está en el JSON de entrada, escribe "No consta". No inventes valores.
    2. ANALÍTICA: Solo rellena Hb, HCT, Plaquetas, INR, TTPA, Creatinina y FG si hay números explícitos.
    3. REGLA DE ERROR: Si la entrada está vacía, responde: "ERROR: No se han detectado datos médicos válidos."

    ### TAREAS:
    1. INFORME TEXTUAL (Formato Valoracion Preanest.txt):
       - Primera línea: "ASA: [X] / APTO: [SÍ/NO/PENDIENTE DE DATOS]".
       - Seguido de salto de línea y el resto del informe (Edad, Peso, Alergias, Antecedentes, Analítica, Recomendaciones).
    2. JSON ESTRUCTURADO (Formato Filler_2.json):
       - Genera el bloque JSON respetando metadatos, configuración y datos (alergias, antecedentes, exploracion, conclusiones, estadoFisico).
    """
    
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system", 
                "content": "Eres un anestesiólogo clínico estricto. Tu prioridad es la seguridad. Si el dato no está presente, no lo asumas ni lo inventes."
            },
            {"role": "user", "content": prompt_maestro}
        ],
        "temperature": 0.0  # Seguridad máxima: elimina la creatividad de la IA
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
