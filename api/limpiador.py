from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
import os

def limpiar_informe_medico(texto_sucio):
    # ... (AQUÍ VA TU FUNCIÓN DE LIMPIEZA EXACTAMENTE COMO LA TENÍAS) ...
    # (Para ahorrar espacio no la pego entera, pero mantenla arriba de todo)
    resultado = {
        "fecha_informe": "",
        "historial_clinico": [],
        "medicacion": [],
        "analitica": []
    }
    # ... (todo tu código de re.search, split, etc.) ...
    return resultado # IMPORTANTE: Ahora devolvemos el DICCIONARIO, no el JSON.

def consultar_llm(datos_limpios, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    # Preparamos la pregunta para la IA
    prompt = f"""
    Actúa como un médico experto. He extraído estos datos de un informe:
    {json.dumps(datos_limpios, ensure_ascii=False)}
    
    Por favor, analiza la información y proporciona:
    1. Un resumen ejecutivo de la situación (2 frases).
    2. Alertas si hay valores de analítica fuera de rango.
    3. Una breve observación sobre la medicación actual.
    
    Responde de forma profesional y concisa.
    """
    
    body = {
        "model": "llama-3.3-70b-versatile", # El modelo más potente de Groq
        "messages": [
            {"role": "system", "content": "Eres un asistente médico experto en análisis de datos estructurados."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {api_key}')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except Exception as e:
        return f"Error al consultar Groq: {str(e)}"

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
            
            # 1. Limpiamos con tu lógica de Python
            datos_limpios = limpiar_informe_medico(texto_sucio)
            
            # 2. Consultamos a Groq (usando la key que enviaremos desde la extensión o Vercel)
            # Para esta prueba, la recibiremos en el body desde la extensión
            api_key = body.get('apiKey', '')
            analisis_ia = consultar_llm(datos_limpios, api_key)
            
            # 3. Devolvemos TODO: los datos limpios + el análisis de la IA
            respuesta_final = {
                "datos_estructurados": datos_limpios,
                "analisis_ia": analisis_ia
            }
            
            self.wfile.write(json.dumps(respuesta_final, indent=2, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
