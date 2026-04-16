from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error

def limpiar_informe_medico(texto_sucio):
    resultado = {
        "fecha_informe": "",
        "historial_clinico": [],
        "medicacion": [],
        "analitica": []
    }
    match_fecha = re.search(r'Fecha:\s*(\d{1,2}/\d{1,2}/\d{4},\s*\d{2}:\d{2}:\d{2})', texto_sucio)
    if match_fecha:
        resultado["fecha_informe"] = match_fecha.group(1)

    if "=== SECCIÓN 1: HISTORIAL CLÍNICO ===" in texto_sucio:
        sec_hist = texto_sucio.split("=== SECCIÓN 1:")[1].split("=== SECCIÓN 2:")[0]
        lineas_hist = [l.strip() for l in sec_hist.split('\n') if l.strip()]
        for i, linea in enumerate(lineas_hist):
            if re.match(r'^\d{2}/\d{2}/\d{4}', linea) and i + 1 < len(lineas_hist):
                diagnostico = lineas_hist[i+1]
                if not diagnostico.startswith("("): 
                    resultado["historial_clinico"].append({"Fecha": linea, "Diagnostico": diagnostico})

    if "=== SECCIÓN 2: MEDICACIÓN ACTIVA ===" in texto_sucio:
        sec_med = texto_sucio.split("=== SECCIÓN 2: MEDICACIÓN ACTIVA ===")[1].split("=== SECCIÓN 3:")[0]
        lineas_med = [l.strip() for l in sec_med.split('\n') if l.strip() and l != "FECHA\tMEDICAMENTO"]
        i = 0
        while i < len(lineas_med):
            linea = lineas_med[i]
            if any(k in linea for k in ["MG", "AMP", "SOL", "ML", "UI"]):
                partes = linea.split('\t')
                resultado["medicacion"].append({
                    "Farmaco": partes[0].strip(), "Dosis": partes[1].strip() if len(partes) > 1 else "",
                    "Unidad": lineas_med[i+1] if i+1 < len(lineas_med) else "",
                    "Frecuencia": lineas_med[i+2] if i+2 < len(lineas_med) else ""
                })
                i += 3
            else: i += 1

    if "=== SECCIÓN 3: ANALÍTICA ===" in texto_sucio:
        sec_ana = texto_sucio.split("=== SECCIÓN 3: ANALÍTICA ===")[1]
        lineas_ana = [l.strip() for l in sec_ana.split('\n') if l.strip()]
        prueba_actual = None
        for linea in lineas_ana:
            if any(r in linea for r in ["BIOQUIMICA", "HEMATIMETRIA", "HEMOSTASIA", "Procedencia", "URL:"]): continue
            if ":" in linea:
                if prueba_actual: resultado["analitica"].append(prueba_actual)
                prueba_actual = {"Prueba": linea.split(":")[0].strip(), "Valor": "", "Rango": "", "Unidad": ""}
            elif re.match(r'^[><]?\d+([,.]\d+)?$', linea) and prueba_actual: prueba_actual["Valor"] = linea
            elif re.match(r'^[\d,.]+\s*-\s*[\d,.]+$', linea) and prueba_actual: prueba_actual["Rango"] = linea
            elif prueba_actual and len(linea) < 15 and not re.match(r'^[><]?\d', linea): prueba_actual["Unidad"] = linea
        if prueba_actual: resultado["analitica"].append(prueba_actual)
    return resultado

def consultar_groq(datos_limpios, api_key):
    url = "[https://api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions)"
    prompt_maestro = f"""
    Actúa como Anestesiólogo experto. Analiza estos datos: {json.dumps(datos_limpios, ensure_ascii=False)}

    TAREA 1: INFORME TEXTUAL (Formato Valoracion Preanest.txt)
    - Calcula el ASA basándote en los antecedentes y medicación.
    - Primera línea: "ASA: [X] / APTO: [SÍ/NO]".
    - Analítica: Extrae Hb, HCT, Plaquetas, INR, TTPA, Creatinina, FG. Si no hay, pon "No consta".

    TAREA 2: JSON ESTRUCTURADO (Formato Filler_2.json)
    - Genera el JSON completo respetando la estructura de metadatos, configuracion y datos.

    REGLA CRÍTICA DE SALIDA:
    Escribe primero el informe de texto. Luego, escribe el JSON encerrado exactamente así:
    ```json
    {{ ... }}
    ```
    No inventes datos. Temperatura 0.
    """
    body = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": "Anestesiólogo estricto. No inventas."}, {"role": "user", "content": prompt_maestro}], "temperature": 0.0}
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except Exception as e: return f"Error: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length).decode('utf-8'))
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin
