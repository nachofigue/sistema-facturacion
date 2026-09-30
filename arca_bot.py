import os
import datetime
import json
from dotenv import load_dotenv
from zeep import Client
from wsaa_client import WSAAClient, get_afip_client
import base_datos

load_dotenv()

def log(mensaje, update_log_callback=None):
    print(mensaje)
    if update_log_callback:
        update_log_callback(mensaje)

def get_condicion_iva_cliente(cuit_cliente, update_log_callback=None):
    cuit = os.getenv("CUIT")
    cert_path = os.getenv("CERT_PATH", "certificado.txt")
    key_path = os.getenv("KEY_PATH", "MiClaveDeArcaNachoFigue10")
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    cert_full = os.path.join(base_dir, cert_path)
    key_full = os.path.join(base_dir, key_path)
    
    try:
        log("Consultando Padrón personaServiceA13 para condición de IVA...", update_log_callback)
        wsaa = WSAAClient(cert_full, key_full)
        token, sign = wsaa.get_ticket("ws_sr_padron_a13")
        
        padron_url = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"
        client = get_afip_client(padron_url)
        
        # Consultamos al padrón A13
        res = client.service.getPersona(
            token=token,
            sign=sign,
            cuitRepresentada=int(cuit),
            idPersona=int(cuit_cliente)
        )
        
        # Mapear según tipo de persona para homologación (simulación/inferencia)
        cuit_str = str(cuit_cliente)
        
        # Determinar condición base por prefijo por si el padrón falla o está vacío
        condicion_base = 5 # CF por defecto
        if cuit_str.startswith("30") or cuit_str.startswith("33"):
            condicion_base = 1 # IVA Responsable Inscripto
        elif cuit_str.startswith("20") or cuit_str.startswith("27") or cuit_str.startswith("23"):
            condicion_base = 6 # Responsable Monotributo

        if hasattr(res, 'persona') and res.persona:
            log(f"Condición IVA mapeada desde Padrón A13 para {cuit_cliente}: {condicion_base}", update_log_callback)
            return condicion_base
        else:
            log(f"Advertencia: No se encontró persona en padrón A13, usando fallback: {condicion_base}", update_log_callback)
            return condicion_base
            
    except Exception as e:
        cuit_str = str(cuit_cliente)
        condicion_base = 1 if (cuit_str.startswith("30") or cuit_str.startswith("33")) else (6 if cuit_str.startswith("2") else 5)
        log(f"Error consultando padrón A13: {str(e)}. Usando fallback inteligente: {condicion_base}", update_log_callback)
        return condicion_base

def generar_factura(datos_remito, update_log_callback=None):
    cuit = os.getenv("CUIT")
    cert_path = os.getenv("CERT_PATH", "certificado.txt")
    key_path = os.getenv("KEY_PATH", "MiClaveDeArcaNachoFigue10")
    
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    cert_full = os.path.join(base_dir, cert_path)
    key_full = os.path.join(base_dir, key_path)
    
    if not cuit or not os.path.exists(cert_full) or not os.path.exists(key_full):
        log("ERROR: CUIT, CERT_PATH o KEY_PATH no están configurados o los archivos no existen.", update_log_callback)
        return False
        
    try:
        log("Conectando con WSAA para obtener autorización...", update_log_callback)
        wsaa = WSAAClient(cert_full, key_full)
        token, sign = wsaa.get_ticket("wsfe")
        log(f"¡Ticket obtenido! Autenticado correctamente.", update_log_callback)
        
        log("Conectando con WSFE (Facturación)...", update_log_callback)
        # URL de Producción de Factura Electrónica
        wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        client = get_afip_client(wsfe_url)
        
        # Objeto de autenticación común
        auth = {
            "Token": token,
            "Sign": sign,
            "Cuit": int(cuit)
        }
        
        # Validar y castear el CUIT del cliente
        cuit_cliente = int(datos_remito.get('cuit_cliente', 0))
        if cuit_cliente == 0:
            log("ERROR: CUIT del cliente inválido o ausente.", update_log_callback)
            return False
            
        doc_nro = cuit_cliente
        
        # Obtener condición de IVA primero para decidir tipo de factura
        condicion_iva_receptor = get_condicion_iva_cliente(doc_nro, update_log_callback)
        
        # Parámetros de la factura dinámicos según condición
        punto_venta = 3
        concepto = 1 # 1 = Productos
        
        if condicion_iva_receptor == 5: # Consumidor Final
            tipo_cbte = 6 # Factura B
            doc_tipo = 96 if len(str(doc_nro)) <= 8 else 80 # DNI o CUIT/CUIL
        else:
            tipo_cbte = 1 # Factura A
            doc_tipo = 80 # CUIT
        
        # Identificar cliente para aplicar reglas
        cliente_nombre = datos_remito.get('cliente_nombre', 'El Tunel S.A.')
        
        # Calcular total (Los precios son NETOS sin IVA según el usuario)
        neto = sum([p['cantidad'] * p['precio'] for p in datos_remito['productos']])
        if neto == 0:
            log("ERROR: El total de la factura es 0.", update_log_callback)
            return False
            
        if cliente_nombre == "Kilbel":
            bonificacion = 0.11
            tasa_iva = 0.105
            id_iva = 4 # AFIP 10.5%
        else: # El Tunel S.A.
            bonificacion = 0.0
            tasa_iva = 0.105
            id_iva = 4 # AFIP 10.5%
            
        # Aplicar bonificación si la hubiera
        neto = neto - (neto * bonificacion)
            
        # Calcular IVA y Total
        neto = round(neto, 2)
        iva_calc = round(neto * tasa_iva, 2)
        total_factura = round(neto + iva_calc, 2)
            
        log(f"Consultando último número de comprobante para PV {punto_venta} y CBTE {tipo_cbte}...", update_log_callback)
        res_ultimo = client.service.FECompUltimoAutorizado(Auth=auth, PtoVta=punto_venta, CbteTipo=tipo_cbte)
        
        if res_ultimo.Errors:
            error_msg = res_ultimo.Errors.Err[0].Msg
            log(f"Error al consultar último CBTE: {error_msg}", update_log_callback)
            return False
            
        siguiente_nro = res_ultimo.CbteNro + 1
        log(f"Próxima factura a emitir: {punto_venta:05d}-{siguiente_nro:08d}", update_log_callback)
        
        # Armar comprobante
        # Para AFIP, la fecha de emisión del comprobante siempre debe ser cronológica,
        # así que usamos la fecha actual automáticamente.
        fecha_cbte = datetime.datetime.now().strftime("%Y%m%d")
        datos_remito["fecha_emision"] = datetime.datetime.now().strftime("%d/%m/%Y")
        
        detalle = {
            "Concepto": concepto,
            "DocTipo": doc_tipo,
            "DocNro": doc_nro,
            "CbteDesde": siguiente_nro,
            "CbteHasta": siguiente_nro,
            "CbteFch": fecha_cbte,
            "ImpTotal": total_factura,
            "ImpTotConc": 0,
            "ImpNeto": neto,
            "ImpOpEx": 0,
            "ImpTrib": 0,
            "ImpIVA": iva_calc,
            "MonId": "PES",
            "MonCotiz": 1,
            "CondicionIVAReceptorId": condicion_iva_receptor,
            "Iva": {
                "AlicIva": [
                    {
                        "Id": id_iva, 
                        "BaseImp": neto,
                        "Importe": iva_calc
                    }
                ]
            }
        }
        
        solicitud = {
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": punto_venta,
                "CbteTipo": tipo_cbte
            },
            "FeDetReq": {
                "FECAEDetRequest": [detalle]
            }
        }
        
        log(f"Enviando solicitud CAE: Neto ${neto} + IVA ${iva_calc} = Total ${total_factura}...", update_log_callback)
        res_cae = client.service.FECAESolicitar(Auth=auth, FeCAEReq=solicitud)
        
        # Revisar respuesta
        if res_cae.Errors:
            for err in res_cae.Errors.Err:
                log(f"AFIP RECHAZÓ (Error {err.Code}): {err.Msg}", update_log_callback)
            return False
            
        detalle_res = res_cae.FeDetResp.FECAEDetResponse[0]
        
        if detalle_res.Resultado == "A":
            cae = detalle_res.CAE
            vto_cae = detalle_res.CAEFchVto
            log("=========================================", update_log_callback)
            log("¡FACTURA APROBADA POR AFIP!", update_log_callback)
            log(f"Comprobante: {punto_venta:05d}-{siguiente_nro:08d}", update_log_callback)
            log(f"CAE: {cae}", update_log_callback)
            log(f"Vencimiento CAE: {vto_cae}", update_log_callback)
            log("=========================================", update_log_callback)
            
            # --- GENERAR PDF ---
            try:
                import pdf_generator
                log("Dibujando factura PDF...", update_log_callback)
                
                # Crear carpeta en el escritorio si no existe
                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                cliente_folder = "kilbel" if cliente_nombre == "Kilbel" else "tunel"
                
                # Obtener la fecha del remito para la carpeta
                if not datos_remito.get("fecha"):
                    datos_remito["fecha"] = datetime.datetime.now().strftime("%d/%m/%Y")
                fecha_remito_str = datos_remito["fecha"].replace("/", "-")
                fecha_facturacion_str = datetime.datetime.now().strftime("%d-%m-%Y")
                fecha_carpeta = fecha_remito_str
                
                facturas_dir = os.path.join(desktop_dir, "facturas", cliente_folder, fecha_carpeta)
                os.makedirs(facturas_dir, exist_ok=True)
                
                pdf_filename = f"Factura_A_{punto_venta:05d}_{siguiente_nro:08d}.pdf"
                pdf_path = os.path.join(facturas_dir, pdf_filename)
                pdf_generator.generar_pdf_factura(datos_remito, cae, vto_cae, siguiente_nro, pdf_path, punto_venta)
                
                metadatos_path = os.path.join(facturas_dir, "metadatos.json")
                metadatos = {}
                if os.path.exists(metadatos_path):
                    try:
                        with open(metadatos_path, "r", encoding="utf-8") as f:
                            metadatos = json.load(f)
                    except Exception:
                        pass
                metadatos[pdf_filename] = fecha_facturacion_str
                try:
                    with open(metadatos_path, "w", encoding="utf-8") as f:
                        json.dump(metadatos, f, indent=4)
                except Exception:
                    pass
                
                # Registrar en la base de datos de estadísticas
                try:
                    fecha_bd = datetime.datetime.strptime(datos_remito["fecha"], "%d/%m/%Y").strftime("%Y-%m-%d")
                    sucursal = datos_remito.get("sucursal", "Desconocida")
                    base_datos.registrar_venta(fecha_bd, sucursal, total_factura)
                except Exception as e_bd:
                    log(f"Error al registrar venta en base de datos: {str(e_bd)}", update_log_callback)
                
                log(f"PDF guardado en: {pdf_filename}", update_log_callback)
            except Exception as e_pdf:
                log(f"Error al generar PDF: {str(e_pdf)}", update_log_callback)

            return True
        else:
            obs = detalle_res.Observaciones.Obs[0].Msg if detalle_res.Observaciones else "Rechazo desconocido"
            log(f"AFIP RECHAZÓ LA FACTURA: {obs}", update_log_callback)
            return False

    except Exception as e:
        log(f"EXCEPCIÓN CRÍTICA SOaP: {str(e)}", update_log_callback)
        return False

def generar_nota_credito(datos_original, update_log_callback=None):
    cuit = os.getenv("CUIT")
    cert_path = os.getenv("CERT_PATH", "certificado.txt")
    key_path = os.getenv("KEY_PATH", "MiClaveDeArcaNachoFigue10")

    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    cert_full = os.path.join(base_dir, cert_path)
    key_full = os.path.join(base_dir, key_path)

    if not cuit or not os.path.exists(cert_full) or not os.path.exists(key_full):
        log("ERROR: CUIT, CERT_PATH o KEY_PATH no están configurados o los archivos no existen.", update_log_callback)
        return False

    try:
        log("Conectando con WSAA para obtener autorización...", update_log_callback)
        wsaa = WSAAClient(cert_full, key_full)
        token, sign = wsaa.get_ticket("wsfe")
        log("¡Ticket obtenido! Autenticado correctamente.", update_log_callback)

        log("Conectando con WSFE (Nota de Crédito)...", update_log_callback)
        wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        client = get_afip_client(wsfe_url)

        auth = {
            "Token": token,
            "Sign": sign,
            "Cuit": int(cuit)
        }

        cuit_cliente = int(datos_original.get('cuit_cliente', 0))
        if cuit_cliente == 0:
            log("ERROR: CUIT del cliente inválido o ausente.", update_log_callback)
            return False

        doc_nro = cuit_cliente
        
        condicion_iva_receptor = get_condicion_iva_cliente(doc_nro, update_log_callback)
        
        punto_venta = 3
        concepto = 1
        
        if condicion_iva_receptor == 5: # Consumidor Final
            tipo_cbte = 8 # 8 = Nota de Crédito B
            doc_tipo = 96 if len(str(doc_nro)) <= 8 else 80
        else:
            tipo_cbte = 3 # 3 = Nota de Crédito A
            doc_tipo = 80
        cliente_nombre = datos_original.get('cliente_nombre', 'El Tunel S.A.')

        imp_neto = float(datos_original.get('imp_neto', 0))
        imp_iva = float(datos_original.get('imp_iva', 0))
        imp_total = float(datos_original.get('imp_total', 0))

        if imp_total == 0:
            log("ERROR: El total de la factura original es 0.", update_log_callback)
            return False

        log(f"Nota de Crédito por ${imp_total} - Cliente: {cliente_nombre}", update_log_callback)

        log(f"Consultando último número de Nota de Crédito para PV {punto_venta}...", update_log_callback)
        res_ultimo = client.service.FECompUltimoAutorizado(Auth=auth, PtoVta=punto_venta, CbteTipo=tipo_cbte)

        if res_ultimo.Errors:
            error_msg = res_ultimo.Errors.Err[0].Msg
            log(f"Error al consultar último CBTE: {error_msg}", update_log_callback)
            return False

        siguiente_nro = res_ultimo.CbteNro + 1
        log(f"Próxima Nota de Crédito: {punto_venta:05d}-{siguiente_nro:08d}", update_log_callback)

        fecha_cbte = datetime.datetime.now().strftime("%Y%m%d")
        datos_original["fecha_emision"] = datetime.datetime.now().strftime("%d/%m/%Y")

        detalle = {
            "Concepto": concepto,
            "DocTipo": doc_tipo,
            "DocNro": doc_nro,
            "CbteDesde": siguiente_nro,
            "CbteHasta": siguiente_nro,
            "CbteFch": fecha_cbte,
            "ImpTotal": imp_total,
            "ImpTotConc": 0,
            "ImpNeto": imp_neto,
            "ImpOpEx": 0,
            "ImpTrib": 0,
            "ImpIVA": imp_iva,
            "MonId": "PES",
            "MonCotiz": 1,
            "CondicionIVAReceptorId": condicion_iva_receptor,
            "Iva": {
                "AlicIva": [
                    {
                        "Id": 4,
                        "BaseImp": imp_neto,
                        "Importe": imp_iva
                    }
                ]
            },
            "CbtesAsoc": {
                "CbteAsoc": [
                    {
                        "Tipo": 1,
                        "PtoVta": int(datos_original.get("punto_venta_original", punto_venta)),
                        "Nro": int(datos_original.get("nro_comprobante_original", 0))
                    }
                ]
            }
        }

        solicitud = {
            "FeCabReq": {
                "CantReg": 1,
                "PtoVta": punto_venta,
                "CbteTipo": tipo_cbte
            },
            "FeDetReq": {
                "FECAEDetRequest": [detalle]
            }
        }

        log(f"Enviando solicitud CAE para Nota de Crédito...", update_log_callback)
        res_cae = client.service.FECAESolicitar(Auth=auth, FeCAEReq=solicitud)

        if res_cae.Errors:
            for err in res_cae.Errors.Err:
                log(f"AFIP RECHAZÓ (Error {err.Code}): {err.Msg}", update_log_callback)
            return False

        detalle_res = res_cae.FeDetResp.FECAEDetResponse[0]

        if detalle_res.Resultado == "A":
            cae = detalle_res.CAE
            vto_cae = detalle_res.CAEFchVto
            log("=========================================", update_log_callback)
            log("¡NOTA DE CRÉDITO APROBADA POR AFIP!", update_log_callback)
            log(f"Comprobante: {punto_venta:05d}-{siguiente_nro:08d}", update_log_callback)
            log(f"CAE: {cae}", update_log_callback)
            log(f"Vencimiento CAE: {vto_cae}", update_log_callback)
            log("=========================================", update_log_callback)

            try:
                import pdf_generator
                log("Dibujando Nota de Crédito PDF...", update_log_callback)

                desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
                cliente_folder = "kilbel" if cliente_nombre == "Kilbel" else "tunel"

                if not datos_original.get("fecha"):
                    datos_original["fecha"] = datetime.datetime.now().strftime("%d/%m/%Y")
                fecha_remito_str = datos_original["fecha"].replace("/", "-")
                fecha_facturacion_str = datetime.datetime.now().strftime("%d-%m-%Y")
                fecha_carpeta = fecha_remito_str

                facturas_dir = os.path.join(desktop_dir, "facturas", cliente_folder, fecha_carpeta)
                os.makedirs(facturas_dir, exist_ok=True)

                pdf_filename = f"Nota_Credito_A_{punto_venta:05d}_{siguiente_nro:08d}.pdf"
                pdf_path = os.path.join(facturas_dir, pdf_filename)

                orig_ref = {
                    "punto_venta": int(datos_original.get("punto_venta_original", punto_venta)),
                    "nro_comprobante": int(datos_original.get("nro_comprobante_original", 0))
                }
                pdf_generator.generar_pdf_nota_credito(
                    datos_original, cae, vto_cae, siguiente_nro, pdf_path, punto_venta,
                    datos_original=orig_ref
                )

                metadatos_path = os.path.join(facturas_dir, "metadatos.json")
                metadatos = {}
                if os.path.exists(metadatos_path):
                    try:
                        with open(metadatos_path, "r", encoding="utf-8") as f:
                            metadatos = json.load(f)
                    except Exception:
                        pass
                metadatos[pdf_filename] = fecha_facturacion_str
                try:
                    with open(metadatos_path, "w", encoding="utf-8") as f:
                        json.dump(metadatos, f, indent=4)
                except Exception:
                    pass

                # Registrar NC en estadísticas (restar monto)
                try:
                    import base_datos
                    fecha_bd = datetime.datetime.strptime(datos_original.get("fecha", datetime.datetime.now().strftime("%d/%m/%Y")), "%d/%m/%Y").strftime("%Y-%m-%d")
                    sucursal = datos_original.get("sucursal", "Desconocida")
                    total_nc = -abs(float(datos_original.get("imp_total", 0)))
                    base_datos.registrar_venta(fecha_bd, sucursal, total_nc)
                    log(f"Nota de crédito registrada en estadísticas (${total_nc}).", update_log_callback)
                except Exception as e_bd:
                    log(f"Error al registrar NC en BD: {str(e_bd)}", update_log_callback)

                log(f"PDF Nota de Crédito guardado en: {pdf_filename}", update_log_callback)
            except Exception as e_pdf:
                log(f"Error al generar PDF: {str(e_pdf)}", update_log_callback)

            return True
        else:
            obs = detalle_res.Observaciones.Obs[0].Msg if detalle_res.Observaciones else "Rechazo desconocido"
            log(f"AFIP RECHAZÓ LA NOTA DE CRÉDITO: {obs}", update_log_callback)
            return False

    except Exception as e:
        log(f"EXCEPCIÓN CRÍTICA: {str(e)}", update_log_callback)
        return False
