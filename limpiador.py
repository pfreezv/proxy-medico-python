from http.server import BaseHTTPRequestHandler
import json
import re

# 1. TU FUNCIÓN EXACTA (El "Cerebro")
def limpiar_informe_medico(texto_bruto):
    datos_limpios = {
        "analitica": [],
        "medicacion": []
    }

    # --- PROCESAMIENTO DE LA ANALÍTICA ---
    if "=== SECCIÓN 3: ANALÍTICA ===" in texto_bruto:
        seccion_analitica = texto_bruto.split("=== SECCIÓN 3: ANALÍTICA ===")[1]
        lineas = [linea.strip() for linea in seccion_analitica.split('\n') if linea.strip()]

        prueba_actual = {}
        for linea in lineas:
            if linea.endswith(':'):
                if prueba_actual:  
                    datos_limpios["analitica"].append(prueba_actual)
                prueba_actual = {"Prueba": linea[:-1].strip()} 
            
            elif "Prueba" in prueba_actual:
                if re.match(r'^[><]?\d+(?:,\d+)?$', linea):
                    prueba_actual["Valor"] = linea
                elif re.match(r'^[\d,]+\s*-\s*[\d,]+$', linea):
                    prueba_actual["Rango"] = linea
                elif re.match(r'^[a-zA-Z0-9/%^\.]+$', linea):
                    prueba_actual["Unidad"] = linea

        if prueba_actual:
            datos_limpios["analitica"].append(prueba_actual)

    # --- PROCESAMIENTO DE LA MEDICACIÓN ---
    if "=== SECCIÓN 2: MEDICACIÓN ACTIVA ===" in texto_bruto:
        seccion_med = texto_bruto.split("=== SECCIÓN 2: MEDICACIÓN ACTIVA ===")[1].split("=== SECCIÓN 3")[0]
        lineas_med = [linea.strip() for linea in seccion_med.split('\n') if linea.strip()]
        
        lineas_med = [l for l in lineas_med if l != "FECHA\tMEDICAMENTO" and l != "FECHA MEDICAMENTO"]
        
        for i in range(0, len(lineas_med), 4):
            if i + 3 < len(lineas_med):
                datos_limpios["medicacion"].append({
                    "Farmaco": lineas_med[i],
                    "Dosis": lineas_med[i+1],
                    "Unidad": lineas_med[i+2],
                    "Frecuencia": lineas_med[i+3]
                })

    return json.dumps(datos_limpios, indent=4, ensure_ascii=False)


# 2. LA CLASE SERVIDORA (El "Mensajero")
class handler(BaseHTTPRequestHandler):
    
    # Manejador del Pre-vuelo (CORS) - Evita el bloqueo del navegador
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # Manejador de la Petición Principal (Cuando la extensión envía el texto)
    def do_POST(self):
        # Respondemos con OK y permitimos CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Averiguamos cuánto pesa el texto enviado y lo leemos
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        try:
            # Traducimos de Bytes a Diccionario Python
            body = json.loads(post_data.decode('utf-8'))
            texto_bruto = body.get('text', '')

            # ¡Ejecutamos tu código!
            resultado_json = limpiar_informe_medico(texto_bruto)

            # Devolvemos el resultado a tu extensión
            self.wfile.write(resultado_json.encode('utf-8'))
            
        except Exception as e:
            # Si algo explota, mandamos el error para depurar
            error_msg = json.dumps({"error": "Falló el procesado en Python", "detalle": str(e)})
            self.wfile.write(error_msg.encode('utf-8'))
