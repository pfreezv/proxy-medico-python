from http.server import BaseHTTPRequestHandler
import json
import re

def limpiar_informe_medico(texto_sucio):
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
                        resultado["historial_clinico"].append({
                            "Fecha": linea,
                            "Diagnostico": diagnostico
                        })

    # 3. SECCIÓN 2: MEDICACIÓN ACTIVA (TU CORRECCIÓN)
    if "=== SECCIÓN 2: MEDICACIÓN ACTIVA ===" in texto_sucio:
        sec_med = texto_sucio.split("=== SECCIÓN 2: MEDICACIÓN ACTIVA ===")[1].split("=== SECCIÓN 3:")[0]
        lineas_med = [l.strip() for l in sec_med.split('\n') if l.strip() and l != "FECHA\tMEDICAMENTO"]
        
        i = 0
        while i < len(lineas_med):
            linea = lineas_med[i]
            if any(k in linea for k in ["MG", "AMP", "SOL", "ML", "UI"]):
                # Separamos el nombre de la dosis numérica que vienen en la misma línea
                partes = linea.split('\t')
                farmaco = partes[0].strip()
                dosis = partes[1].strip() if len(partes) > 1 else ""
                
                resultado["medicacion"].append({
                    "Farmaco": farmaco,
                    "Dosis": dosis,
                    "Unidad": lineas_med[i+1] if i+1 < len(lineas_med) else "",
                    "Frecuencia": lineas_med[i+2] if i+2 < len(lineas_med) else ""
                })
                i += 3 # Ahora saltamos de 3 en 3
            else:
                i += 1

    # 4. SECCIÓN 3: ANALÍTICA (TU CORRECCIÓN)
    if "=== SECCIÓN 3: ANALÍTICA ===" in texto_sucio:
        sec_ana = texto_sucio.split("=== SECCIÓN 3: ANALÍTICA ===")[1]
        lineas_ana = [l.strip() for l in sec_ana.split('\n') if l.strip()]
        
        ruido = ["BIOQUIMICA GENERAL", "HEMATIMETRIA", "HEMOSTASIA", 
                 "Procedencia", "HELL - URGENCIAS", "La información mostrada", "URL:"]
        
        prueba_actual = None
        for linea in lineas_ana:
            if any(r in linea for r in ruido) or linea.startswith("http") or re.match(r'^Fecha:', linea):
                continue
                
            if ":" in linea:
                if prueba_actual: resultado["analitica"].append(prueba_actual)
                prueba_actual = {"Prueba": linea.split(":")[0].strip(), "Valor": "", "Rango": "", "Unidad": ""}
            
            elif re.match(r'^[><]?\d+([,.]\d+)?$', linea) and prueba_actual:
                prueba_actual["Valor"] = linea
            
            elif re.match(r'^[\d,.]+\s*-\s*[\d,.]+$', linea) and prueba_actual:
                prueba_actual["Rango"] = linea
            
            # Unidad: Cualquier línea corta que quede y no empiece por número
            elif prueba_actual and len(linea) < 15 and not re.match(r'^[><]?\d', linea):
                prueba_actual["Unidad"] = linea

        if prueba_actual: resultado["analitica"].append(prueba_actual)

    return json.dumps(resultado, indent=2, ensure_ascii=False)

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
            texto_sucio = body.get('text', '')
            resultado_json = limpiar_informe_medico(texto_sucio)
            self.wfile.write(resultado_json.encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
