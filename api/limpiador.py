from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import urllib.error

def limpiar_informe_medico(texto_sucio):
    """
    Procesamiento de texto basado en las reglas de limpieza definidas. 
    """
    resultado = {
        "fecha_informe": "",
        "historial_clinico": [],
        "medicacion": [],
        "analitica": []
    }

    # 1. Extraer fecha general del informe 
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
    Envía los datos a Groq con el prompt de anestesiología.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt_maestro = f"""
    Actúa como un médico Anestesiólogo experto en medicina preoperatoria. 
    Transforma estos datos estructurados en el formato solicitado.

    ### DATOS DE ENTRADA:
    {json.dumps(datos_limpios, ensure_ascii=False)}

    ### INSTRUCCIONES:
    1. GENERAR INFORME TEXTUAL (Formato Valoracion Preanest.txt):
       Sigue este orden: Edad, Peso, Talla, Alergias, Antecedentes Medicos/Quirurgicos, Analítica (Hb, HCT, Plaquetas, INR, TTPA, Creatinina, FG), Valoración ASA y Recomendaciones.
       * IMPORTANTE: En la Analítica incluye siempre los valores numéricos encontrados en los datos de entrada.
       * OBSERVACIONES: La primera línea debe ser "ASA: [X] / APTO: [SÍ/NO]", seguida de un salto de línea y el resto del análisis.

    2. GENERAR JSON (Estructura Filler_2.json):
       Crea un bloque JSON con la estructura: metadatos, configuracion y datos (alergias, antecedentes, exploracion, conclusiones, estadoFisico).

    Responde de forma profesional. Primero el Informe de Texto y luego el bloque JSON.
    """
    
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Eres un anestesiólogo experto que genera informes y JSON estructurado."},
            {"role": "user", "content": prompt_maestro}
        ],
        "temperature": 0.3
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    # User-Agent para evitar el error 403 Forbidden
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        return f"Error Groq ({e.code}): {error_body}"
    except Exception as e:
        return f"Error inesperado: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        try:
            body = json.loads(post_data.decode('utf-8'))
            # 1. Limpieza con Python 
            datos_limpios = limpiar_informe_medico(body.get('text', ''))
            # 2. Análisis con IA
            analisis_ia = consultar_groq(datos_limpios, body.get('apiKey', ''))
            
            respuesta_final = {
                "datos_estructurados": datos_limpios,
                "analisis_ia": analisis_ia
            }
            self.wfile.write(json.dumps(respuesta_final, indent=2, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
