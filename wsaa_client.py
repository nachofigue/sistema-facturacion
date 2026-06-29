import os
import datetime
import base64
import json
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization.pkcs7 import PKCS7SignatureBuilder, PKCS7Options
from cryptography.hazmat.primitives import hashes
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives import serialization
from zeep import Client

class WSAAClient:
    def __init__(self, cert_path, key_path, url="https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"):
        self.cert_path = cert_path
        self.key_path = key_path
        self.url = url
        self.client = Client(self.url)
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ta_cache.json")

    def generate_tra(self, service="wsfe"):
        root = ET.Element("loginTicketRequest", {"version": "1.0"})
        header = ET.SubElement(root, "header")
        
        now = datetime.datetime.now()
        unique_id = str(int(now.timestamp()))
        generation_time = now - datetime.timedelta(minutes=5)
        expiration_time = now + datetime.timedelta(hours=12)
        
        ET.SubElement(header, "uniqueId").text = unique_id
        ET.SubElement(header, "generationTime").text = generation_time.strftime("%Y-%m-%dT%H:%M:%S")
        ET.SubElement(header, "expirationTime").text = expiration_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        ET.SubElement(root, "service").text = service
        
        xml_str = ET.tostring(root, encoding="utf-8")
        return xml_str

    def sign_tra(self, tra_xml):
        with open(self.cert_path, "rb") as f:
            cert = load_pem_x509_certificate(f.read())
            
        with open(self.key_path, "rb") as f:
            key = load_pem_private_key(f.read(), password=None)
            
        builder = PKCS7SignatureBuilder().set_data(tra_xml)
        builder = builder.add_signer(cert, key, hashes.SHA256())
        cms_bytes = builder.sign(serialization.Encoding.DER, [PKCS7Options.NoAttributes])
        
        return base64.b64encode(cms_bytes).decode("ascii")

    def get_ticket(self, service="wsfe"):
        # 1. Verificar si hay un ticket válido en caché
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    cache = json.load(f)
                
                exp_str = cache.get("expiration_time")
                if exp_str:
                    exp_time = datetime.datetime.fromisoformat(exp_str)
                    # Asegurar que ambas fechas no tengan zona horaria para evitar TypeError
                    exp_time = exp_time.replace(tzinfo=None)
                    
                    # Dejar 10 minutos de margen de seguridad
                    if datetime.datetime.now() < (exp_time - datetime.timedelta(minutes=10)):
                        return cache["token"], cache["sign"]
            except Exception:
                pass # Si el caché falla por algún motivo, ignorar y pedir uno nuevo

        # 2. Si no hay ticket o está expirado, solicitar uno nuevo a AFIP
        tra_xml = self.generate_tra(service)
        cms_base64 = self.sign_tra(tra_xml)
        
        response_xml = self.client.service.loginCms(in0=cms_base64)
        
        root = ET.fromstring(response_xml)
        token = root.find(".//token").text
        sign = root.find(".//sign").text
        
        # 3. Guardar el ticket en caché con 11 horas de validez desde ahora
        exp_time = datetime.datetime.now() + datetime.timedelta(hours=11)
        
        with open(self.cache_file, "w") as f:
            json.dump({
                "token": token,
                "sign": sign,
                "expiration_time": exp_time.isoformat()
            }, f)
        
        return token, sign
