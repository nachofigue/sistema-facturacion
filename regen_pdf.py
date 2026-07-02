import os
import pdf_generator

datos_remito = {
    "cuit_cliente": "30518084557",
    "cliente_nombre": "El Tunel S.A.",
    "fecha_emision": "01/07/2026",
    "orden": "00002",
    "remito": "00004408",
    "sucursal": "Avenida Aristobulo Del Valle 7934 - Santa Fe, Santa Fe",
    "productos": [
        {"nombre": "105", "cantidad": 20.0, "precio": 1750.0},
        {"nombre": "104", "cantidad": 6.0, "precio": 1450.0},
        {"nombre": "zanahoria", "cantidad": 2.0, "precio": 1450.0},
        {"nombre": "sopitas", "cantidad": 7.0, "precio": 2000.0},
        {"nombre": "puchero", "cantidad": 2.0, "precio": 2000.0},
        {"nombre": "provenzal", "cantidad": 5.0, "precio": 2000.0}
    ]
}

cae = "86262002585479"
vto_cae = "20260711" # vto_cae en formato YYYYMMDD según arca_bot.py (o 11/07/2026)
# Espera, en pdf_generator.py:
# vto_cae_str = str(vto_cae)
# if len(vto_cae_str) == 8:
#     vto_cae_fmt = f"{vto_cae_str[6:8]}/{vto_cae_str[4:6]}/{vto_cae_str[0:4]}"
# So I should pass "20260711"

desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
facturas_dir = os.path.join(desktop_dir, "facturas", "tunel", "01-07-2026")
os.makedirs(facturas_dir, exist_ok=True)

pdf_filename = "Factura_A_00003_00000001_CORREGIDA.pdf"
pdf_path = os.path.join(facturas_dir, pdf_filename)

pdf_generator.generar_pdf_factura(datos_remito, cae, "20260711", 1, pdf_path, punto_venta=3)

print(f"PDF generado exitosamente en: {pdf_path}")
