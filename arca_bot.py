import os
import datetime
from dotenv import load_dotenv
from zeep import Client
from wsaa_client import WSAAClient, get_afip_client

load_dotenv()

def log(mensaje, update_log_callback=None):
    print(mensaje)
    if update_log_callback:
        update_log_callback(mensaje)

def generar_factura(datos_remito, update_log_callback=None):
    cuit = os.getenv("CUIT")
    cert_path = os.getenv("CERT_PATH", "certificado.txt")
    key_path = os.getenv("KEY_PATH", "MiClaveDeArcaNachoFigue10")
    
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
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
        
        # Parámetros de la factura (Factura A)
        punto_venta = 3
        tipo_cbte = 1 # 1 = Factura A
        concepto = 1 # 1 = Productos
        doc_tipo = 80 # 80 = CUIT
        
        # Validar y castear el CUIT del cliente
        cuit_cliente = int(datos_remito.get('cuit_cliente', 0))
        if cuit_cliente == 0:
            log("ERROR: CUIT del cliente inválido o ausente.", update_log_callback)
            return False
            
        doc_nro = cuit_cliente
        
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
                fecha_carpeta = datos_remito["fecha"].replace("/", "-")
                
                facturas_dir = os.path.join(desktop_dir, "facturas", cliente_folder, fecha_carpeta)
                os.makedirs(facturas_dir, exist_ok=True)
                
                pdf_filename = f"Factura_A_{punto_venta:05d}_{siguiente_nro:08d}.pdf"
                pdf_path = os.path.join(facturas_dir, pdf_filename)
                pdf_generator.generar_pdf_factura(datos_remito, cae, vto_cae, siguiente_nro, pdf_path, punto_venta)
                
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
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
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

        punto_venta = 3
        tipo_cbte = 3  # 3 = Nota de Crédito A
        concepto = 1
        doc_tipo = 80

        cuit_cliente = int(datos_original.get('cuit_cliente', 0))
        if cuit_cliente == 0:
            log("ERROR: CUIT del cliente inválido o ausente.", update_log_callback)
            return False

        doc_nro = cuit_cliente
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
                fecha_carpeta = datos_original["fecha"].replace("/", "-")

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

                log(f"PDF guardado en: {pdf_filename}", update_log_callback)
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
