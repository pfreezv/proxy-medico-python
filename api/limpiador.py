de http.servidor importar Controlador de solicitud HTTP base
importar json
importar re
# 1. TU FUNCIÓN EXACTA (El "Cerebro")
definición limpiar_informe_médico(texto_bruto):
    datos_limpios ={
        "analítica": [],
        "medicación": []
    }
    # --- PROCESAMIENTO DE LA ANALÍTICA ---
    si "=== SECCIÓN 3: ANALÍTICA ===" en texto_bruto:
        sección_analítica = texto_bruto.dividir("=== SECCIÓN 3: ANALÍTICA ===")[1]
        líneas =[línea.banda()para línea en sección_analítica.dividir('\norte')si línea.banda()]
        prueba_actual ={}
        para línea en líneas:
            si línea.termina con(":"):
                si prueba_actual:  
                    datos_limpios["analítica"].añadir(prueba_actual)
                prueba_actual ={"Prueba":línea[:-1].banda()}
            
            elif "Prueba" en prueba_actual:
                si re.fósforo(r'^[><]?\d+(?:,\d+)?$',línea):
                    prueba_actual["Valor"]= línea
                elif re.fósforo(r'^[\d,]+\s*-\s*[\d,]+$',línea):
                    prueba_actual["Rango"]= línea
                elif re.fósforo(r'^[a-zA-Z0-9/%^\.]+$',línea):
                    prueba_actual["Unidad"]= línea
        si prueba_actual:
            datos_limpios["analítica"].añadir(prueba_actual)
    # --- PROCESAMIENTO DE LA MEDICACIÓN ---
    si "=== SECCIÓN 2: MEDICACIÓN ACTIVA ===" en texto_bruto:
        sección_med = texto_bruto.dividir("=== SECCIÓN 2: MEDICACIÓN ACTIVA ===")[1].dividir("=== SECCIÓN 3")[0]
        líneas_med =[línea.banda()para línea en sección_med.dividir('\norte')si línea.banda()]
        
        líneas_med =[l para l en líneas_med si l != "FECHA\tMEDICAMENTO" y l != "FECHA MEDICAMENTO"]
        
        para i en rango(0,Len(líneas_med),4):
            si i + 3 < Len(líneas_med):
                datos_limpios["medicación"].añadir({
                    "Farmaco":líneas_med[i],
                    "Dosis":líneas_med[i+1],
                    "Unidad":líneas_med[i+2],
                    "Frecuencia":líneas_med[i+3]
                })
    devolver json.deshecho(datos_limpios,sangrar=4,asegurar_ascii=FALSO)
# 2. LA CLASE SERVIDORA (El "Mensajero")
clase entrenador de animales(Controlador de solicitud HTTP base):
    
    # Manejador del Pre-vuelo (CORS) - Evita el bloqueo del navegador
    definición hacer_OPCIONES(ser):
        ser.enviar_respuesta(200)
        ser.enviar_encabezado('Access-Control-Allow-Origin','*')
        ser.enviar_encabezado('Métodos permitidos de control de acceso','PUBLICACIÓN, OPCIONES')
        ser.enviar_encabezado('Access-Control-Allow-Headers','Tipo de contenido')
        ser.fin_de_encabezados()
    # Manejador de la Petición Principal (Cuando la extensión envía el texto)
    definición hacer_POST(ser):
        # Respondemos con OK y permitimos CORS
        ser.enviar_respuesta(200)
        ser.enviar_encabezado('Access-Control-Allow-Origin','*')
        ser.enviar_encabezado('Tipo de contenido','application/json')
        ser.fin_de_encabezados()
        # Averiguamos cuánto pesa el texto enviado y lo leemos
        longitud_del_contenido = entero(ser.encabezados.conseguir('Longitud del contenido',0))
        datos_post = ser.archivo r.leer(longitud_del_contenido)
        intentar:
            # Traducimos de Bytes al Diccionario Python
            cuerpo = json.cargas(datos_post.descodificar('utf-8'))
            texto_bruto = cuerpo.conseguir('texto','')
            # ¡Ejecutamos tu código!
            resultado_json = limpiar_informe_médico(texto_bruto)
            # Devolvemos el resultado a tu extensión
            ser.archivo w.escribir(resultado_json.codificar('utf-8'))
            
        excepto Excepción como mi:
            # Si algo explota, mandamos el error para depurar
            mensaje_de_error = json.deshecho({"error":"Falló el procesado en Python","detalle":str(mi)})
            ser.archivo w.escribir(mensaje_de_error.codificar('utf-8'))
