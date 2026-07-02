import os
from dotenv import load_dotenv
from zeep import Client
from wsaa_client import WSAAClient, get_afip_client

load_dotenv()

def test_conexion():
    cuit = os.getenv("CUIT")
    cert_path = "certificado_real.crt" # Reemplazar con el nombre de tu certificado real una vez descargado
    key_path = "ClaveRealEmpresa.key"
    
    if not cuit:
        print("ERROR: CUIT no configurado en .env")
        return
        
    print(f"Probando conexión para CUIT {cuit} con certificado {cert_path}")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"ATENCIÓN: Aún no tienes los archivos {cert_path} o {key_path}.")
        print("Asegúrate de haber descargado el certificado del portal de ARCA y haberlo nombrado correctamente.")
        return
        
    try:
        print("1. Conectando con WSAA (Producción)...")
        wsaa = WSAAClient(cert_path, key_path)
        token, sign = wsaa.get_ticket("wsfe")
        print("   ¡Ticket obtenido! Autenticado correctamente.")
        
        print("2. Conectando con WSFE (Producción)...")
        wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        client = get_afip_client(wsfe_url)
        
        auth = {
            "Token": token,
            "Sign": sign,
            "Cuit": int(cuit)
        }
        
        punto_venta = 3
        tipo_cbte = 1 # Factura A
        
        print(f"3. Consultando último comprobante para PV {punto_venta} y CBTE {tipo_cbte}...")
        res_ultimo = client.service.FECompUltimoAutorizado(Auth=auth, PtoVta=punto_venta, CbteTipo=tipo_cbte)
        
        if res_ultimo.Errors:
            error_msg = res_ultimo.Errors.Err[0].Msg
            print(f"   Error devuelto por ARCA: {error_msg}")
        else:
            print("=========================================")
            print("¡CONEXIÓN EXITOSA!")
            print(f"Último comprobante autorizado: {res_ultimo.CbteNro}")
            print(f"Siguiente comprobante a emitir: {res_ultimo.CbteNro + 1}")
            print("=========================================")
            
    except Exception as e:
        print(f"ERROR DE CONEXIÓN: {str(e)}")

if __name__ == "__main__":
    test_conexion()
