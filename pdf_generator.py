import os
import json
import io
import datetime
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors

def fmt(value):
    # Formatea un float al estilo argentino (coma para decimales, dos decimales)
    return f"{value:.2f}".replace('.', ',')

def generar_pdf_factura(datos_factura, cae, vto_cae, nro_comprobante, output_path, punto_venta=3):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Pre-calcular totales y desgloses
    neto_total = 0.0
    cliente_nombre = datos_factura.get("cliente_nombre", "Supermercado El Tunel S.A.")
    bonif_pct = 11.0 if cliente_nombre == "Kilbel" else 0.0
    
    for p in datos_factura.get("productos", []):
        bruto = p["cantidad"] * p["precio"]
        descuento = bruto * (bonif_pct / 100.0)
        subtotal_neto = bruto - descuento
        neto_total += subtotal_neto
        
    iva_total = neto_total * 0.105
    total = neto_total + iva_total

    # Definir las copias
    copias = ["ORIGINAL", "DUPLICADO", "TRIPLICADO"]
    
    for idx, copia in enumerate(copias):
        # ---------- ENCABEZADO Y MARGENES ----------
        m_top = height - 30
        m_left = 15
        m_right = width - 15
        m_w = m_right - m_left
        
        # Configuracion de bordes
        c.setLineWidth(0.5)
        c.setStrokeColor(colors.black)
        
        # Recuadro principal superior de la copia (ORIGINAL, DUPLICADO...)
        c.rect(m_left, m_top - 25, m_w, 25)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, m_top - 18, copia)
        
        # Caja principal Header (Emisor / Factura)
        c.rect(m_left, m_top - 175, m_w, 150)
        c.line(width/2, m_top - 175, width/2, m_top - 65) # Linea vertical separadora inferior
        
        # Cuadro Letra A
        c.setFillColor(colors.white)
        c.rect(width/2 - 22, m_top - 65, 44, 40, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width/2, m_top - 50, "A")
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(width/2, m_top - 60, "COD. 01")
        
        # ---- Datos Izquierda (Emisor) ----
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width/4, m_top - 55, "SU BANDEJA")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 100, "Razón Social: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 75, m_top - 100, "MANCINI GISELA PAOLA")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 130, "Domicilio Comercial: ")
        c.setFont("Helvetica", 8)
        c.drawString(m_left + 110, m_top - 130, "Pasaje Lassaga 6950 - Santa Fe, Santa Fe")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 160, "Condición frente al IVA: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 130, m_top - 160, "IVA Responsable Inscripto")
        
        # ---- Datos Derecha (Factura) ----
        c.setFont("Helvetica-Bold", 20)
        c.drawString(width/2 + 40, m_top - 55, "FACTURA")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 85, "Punto de Venta: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 115, m_top - 85, f"{punto_venta:05d}")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 150, m_top - 85, "Comp. Nro: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 205, m_top - 85, f"{nro_comprobante:08d}")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 105, "Fecha de Emisión: ")
        c.setFont("Helvetica", 10)
        fecha_emision = datos_factura.get("fecha_emision", datetime.datetime.now().strftime("%d/%m/%Y"))
        c.drawString(width/2 + 130, m_top - 105, fecha_emision)
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 130, "CUIT: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 70, m_top - 130, "23257812634")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 145, "Ingresos Brutos: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 120, m_top - 145, "011-499274-3")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 160, "Fecha de Inicio de Actividades: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 185, m_top - 160, "01/04/2024")
        
        # ---------- RECEPTOR ----------
        c.rect(m_left, m_top - 255, m_w, 70)
        
        cuit_cliente = str(datos_factura.get("cuit_cliente", ""))
        orden_str = datos_factura.get("orden", "00002")
        remito_str = f"{orden_str}-{int(datos_factura.get('remito', 0)):08d}" if datos_factura.get('remito') else ""
        
        suc = datos_factura.get("sucursal", "").strip()
        
        if cliente_nombre == "Kilbel":
            cliente_nombre_display = "KILBEL S.A."
            domicilio_cliente = suc if suc else "Corrientes 2870 - Santa Fe, Santa Fe"
        else:
            cliente_nombre_display = cliente_nombre
            domicilio_cliente = suc if suc else "Colectora Oeste Ap Rosario Sta Fe Km 151 - Santo Tome, Santa Fe"
            
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 200, "CUIT: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 45, m_top - 200, cuit_cliente)
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 225, "Condición frente al IVA: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 130, m_top - 225, "IVA Responsable Inscripto")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 245, "Condición de venta: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 110, m_top - 245, "Cuenta Corriente")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 80, m_top - 200, "Apellido y Nombre / Razón Social: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 80, m_top - 200, cliente_nombre_display)
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 30, m_top - 225, "Domicilio Comercial: ")
        c.setFont("Helvetica", 8)
        c.drawString(width/2 + 70, m_top - 225, domicilio_cliente)
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 18, m_top - 245, "Remito: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 25, m_top - 245, remito_str)
        
        # ---------- GRILLA PRODUCTOS ----------
        y_grid_top = m_top - 270
        
        # Fondo Cabecera Grilla
        c.setFillColor(colors.lightgrey)
        c.rect(m_left, y_grid_top - 25, m_w, 25, fill=1, stroke=1)
        c.setFillColor(colors.black)
        
        c.setFont("Helvetica-Bold", 7)
        # Tramos X para las columnas (proporciones de la captura)
        cx = [m_left, m_left + 45, m_left + 230, m_left + 270, m_left + 320, m_left + 370, m_left + 410, m_left + 460, m_left + 500, m_right]
        
        c.drawString(cx[1]+5, y_grid_top - 15, "Producto / Servicio")
        c.drawCentredString((cx[2]+cx[3])/2, y_grid_top - 15, "Cantidad")
        c.drawCentredString((cx[3]+cx[4])/2, y_grid_top - 15, "U. medida")
        c.drawCentredString((cx[4]+cx[5])/2, y_grid_top - 15, "Precio Unit.")
        c.drawCentredString((cx[5]+cx[6])/2, y_grid_top - 15, "% Bonif")
        c.drawCentredString((cx[6]+cx[7])/2, y_grid_top - 15, "Subtotal")
        c.drawCentredString((cx[7]+cx[8])/2, y_grid_top - 12, "Alicuota")
        c.drawCentredString((cx[7]+cx[8])/2, y_grid_top - 21, "IVA")
        c.drawCentredString((cx[8]+cx[9])/2, y_grid_top - 15, "Subtotal c/IVA")
        
        # Borde exterior grilla
        c.rect(m_left, 250, m_w, y_grid_top - 275) # Caja de la grilla de productos vacia hasta el total
        
        # Filas de Productos
        y_row = y_grid_top - 40
        c.setFont("Helvetica", 8)
        productos_display = datos_factura.get("productos", [])
        if cliente_nombre != "Kilbel":
            productos_display = []
            for p in datos_factura.get("productos", []):
                cp = dict(p)
                cod = cp.get("codigo_arca", "")
                if cod == "105M":
                    cp["nombre"] = "105"
                elif cod == "104M":
                    cp["nombre"] = "104"
                productos_display.append(cp)
        for p in productos_display:
            bruto = p["cantidad"] * p["precio"]
            descuento = bruto * (bonif_pct / 100.0)
            subtotal_neto = bruto - descuento
            iva_item = subtotal_neto * 0.105
            subtotal_c_iva = subtotal_neto + iva_item
            
            c.drawString(cx[1] + 5, y_row, p.get("nombre", "").lower())
            
            c.drawRightString(cx[3] - 5, y_row, fmt(p["cantidad"]))
            if p.get("es_kg", False):
                c.drawCentredString((cx[3]+cx[4])/2, y_row, "kilogramos")
            else:
                c.drawCentredString((cx[3]+cx[4])/2, y_row, "unidades")
            c.drawRightString(cx[5] - 5, y_row, fmt(p["precio"]))
            c.drawRightString(cx[6] - 5, y_row, fmt(bonif_pct))
            c.drawRightString(cx[7] - 5, y_row, fmt(subtotal_neto))
            c.drawCentredString((cx[7]+cx[8])/2, y_row, "10,5%")
            c.drawRightString(cx[9] - 5, y_row, fmt(subtotal_c_iva))
            
            y_row -= 15
            
        # ---------- CAJA TOTALES ----------
        c.rect(m_left, 100, m_w, 150)
        c.setFont("Helvetica", 10)
        
        c.drawString(m_left + 100, 230, "Importe Otros Tributos: $")
        c.drawString(m_left + 230, 230, "0,00")
        
        c.setFont("Helvetica-Bold", 10)
        tx = width - 150
        vx = width - 35
        
        c.drawRightString(tx, 230, "Importe Neto Gravado: $")
        c.drawRightString(vx, 230, fmt(neto_total))
        
        c.drawRightString(tx, 215, "IVA 27%: $")
        c.drawRightString(vx, 215, "0,00")
        
        c.drawRightString(tx, 200, "IVA 21%: $")
        c.drawRightString(vx, 200, "0,00")
        
        c.drawRightString(tx, 185, "IVA 10.5%: $")
        c.drawRightString(vx, 185, fmt(iva_total))
        
        c.drawRightString(tx, 170, "IVA 5%: $")
        c.drawRightString(vx, 170, "0,00")
        
        c.drawRightString(tx, 155, "IVA 2.5%: $")
        c.drawRightString(vx, 155, "0,00")
        
        c.drawRightString(tx, 140, "IVA 0%: $")
        c.drawRightString(vx, 140, "0,00")
        
        c.drawRightString(tx, 125, "Importe Otros Tributos: $")
        c.drawRightString(vx, 125, "0,00")
        
        c.drawRightString(tx, 110, "Importe Total: $")
        c.drawRightString(vx, 110, fmt(total))
        
        # ---------- FOOTER Y QR ----------
        # Logo ARCA (Texto Estructurado)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(120, 75, "ARCA")
        
        c.setLineWidth(1)
        c.line(120, 70, 260, 70)
        
        c.setFont("Helvetica", 6)
        c.drawString(120, 62, "AGENCIA DE RECAUDACIÓN")
        c.drawString(120, 55, "Y CONTROL ADUANERO")
        
        c.setFont("Helvetica-Bold", 9)
        c.drawString(120, 35, "Comprobante Autorizado")
        c.setFont("Helvetica-BoldOblique", 7)
        c.drawString(120, 20, "Esta Agencia no se responsabiliza por los datos ingresados en el detalle de la operación")
        
        # Paginacion
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, 50, "Pág. 1/1")
        
        # CAE y Vto
        c.drawRightString(width - 150, 50, "CAE N°: ")
        c.setFont("Helvetica", 10)
        c.drawString(width - 145, 50, str(cae))
        
        # Formatear Vto CAE (YYYYMMDD -> DD/MM/YYYY)
        vto_cae_str = str(vto_cae)
        if len(vto_cae_str) == 8:
            vto_cae_fmt = f"{vto_cae_str[6:8]}/{vto_cae_str[4:6]}/{vto_cae_str[0:4]}"
        else:
            vto_cae_fmt = vto_cae_str
            
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 150, 35, "Fecha de Vto. de CAE: ")
        c.setFont("Helvetica", 10)
        c.drawString(width - 145, 35, vto_cae_fmt)
        
        # QR Code
        import base64
        
        try:
            fecha_qr = datetime.datetime.strptime(fecha_emision, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            fecha_qr = fecha_emision.replace('/', '-')
            
        qr_data = {
            "ver": 1,
            "fecha": fecha_qr,
            "cuit": 23257812634,
            "ptoVta": punto_venta,
            "tipoCmp": 1,
            "nroCmp": nro_comprobante,
            "importe": total,
            "moneda": "PES",
            "ctz": 1,
            "tipoDocRec": 80,
            "nroDocRec": int(cuit_cliente) if cuit_cliente else 0,
            "tipoCodAut": "E",
            "codAut": int(cae)
        }
        
        json_qr = json.dumps(qr_data)
        b64_qr = base64.b64encode(json_qr.encode('utf-8')).decode('utf-8')
        qr_url = f"https://servicioscf.afip.gob.ar/publico/comprobantes/cae.aspx?p={b64_qr}"
        
        img = qrcode.make(qr_url)
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        # Ajustar el QR para que quede cuadrado perfecto de unos 70x70
        c.drawImage(ImageReader(qr_buffer), m_left + 5, 20, 75, 75)
        
        # Finalizar la pagina y pasar a la siguiente copia
        if idx < len(copias) - 1:
            c.showPage()
            
    c.save()

def generar_pdf_nota_credito(datos_factura, cae, vto_cae, nro_comprobante, output_path,
                              punto_venta=3, datos_original=None):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    neto_total = 0.0
    cliente_nombre = datos_factura.get("cliente_nombre", "Supermercado El Tunel S.A.")
    bonif_pct = 11.0 if cliente_nombre == "Kilbel" else 0.0

    for p in datos_factura.get("productos", []):
        bruto = p["cantidad"] * p["precio"]
        descuento = bruto * (bonif_pct / 100.0)
        subtotal_neto = bruto - descuento
        neto_total += subtotal_neto

    iva_total = neto_total * 0.105
    total = neto_total + iva_total

    copias = ["ORIGINAL", "DUPLICADO", "TRIPLICADO"]

    for idx, copia in enumerate(copias):
        m_top = height - 30
        m_left = 15
        m_right = width - 15
        m_w = m_right - m_left

        c.setLineWidth(0.5)
        c.setStrokeColor(colors.black)

        c.rect(m_left, m_top - 25, m_w, 25)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, m_top - 18, copia)

        c.rect(m_left, m_top - 175, m_w, 150)
        c.line(width/2, m_top - 175, width/2, m_top - 65)

        c.setFillColor(colors.white)
        c.rect(width/2 - 22, m_top - 65, 44, 40, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 30)
        c.drawCentredString(width/2, m_top - 50, "A")
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(width/2, m_top - 60, "COD. 03")

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width/4, m_top - 55, "SU BANDEJA")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 100, "Razón Social: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 75, m_top - 100, "MANCINI GISELA PAOLA")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 130, "Domicilio Comercial: ")
        c.setFont("Helvetica", 8)
        c.drawString(m_left + 110, m_top - 130, "Pasaje Lassaga 6950 - Santa Fe, Santa Fe")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 160, "Condición frente al IVA: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 130, m_top - 160, "IVA Responsable Inscripto")

        c.setFont("Helvetica-Bold", 20)
        c.drawString(width/2 + 40, m_top - 55, "NOTA DE CRÉDITO")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 85, "Punto de Venta: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 115, m_top - 85, f"{punto_venta:05d}")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 150, m_top - 85, "Comp. Nro: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 205, m_top - 85, f"{nro_comprobante:08d}")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 105, "Fecha de Emisión: ")
        c.setFont("Helvetica", 10)
        fecha_emision = datos_factura.get("fecha_emision", datetime.datetime.now().strftime("%d/%m/%Y"))
        c.drawString(width/2 + 130, m_top - 105, fecha_emision)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 130, "CUIT: ")
        c.setFont("Helvetica", 10)
        c.drawString(width/2 + 70, m_top - 130, "23257812634")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 145, "Ingresos Brutos: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 120, m_top - 145, "011-499274-3")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 + 40, m_top - 160, "Fecha de Inicio de Actividades: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 185, m_top - 160, "01/04/2024")

        c.rect(m_left, m_top - 285, m_w, 100)

        cuit_cliente = str(datos_factura.get("cuit_cliente", ""))
        orden_str = datos_factura.get("orden", "00002")
        remito_str = f"{orden_str}-{int(datos_factura.get('remito', 0)):08d}" if datos_factura.get('remito') else ""

        suc = datos_factura.get("sucursal", "").strip()

        if cliente_nombre == "Kilbel":
            cliente_nombre_display = "KILBEL S.A."
            domicilio_cliente = suc if suc else "Corrientes 2870 - Santa Fe, Santa Fe"
        else:
            cliente_nombre_display = "SUPERMERCADO EL TUNEL SA S. A."
            domicilio_cliente = suc if suc else "Colectora Oeste Ap Rosario Sta Fe Km 151 - Santo Tome, Santa Fe"

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 200, "CUIT: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 45, m_top - 200, cuit_cliente)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 225, "Condición frente al IVA: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 130, m_top - 225, "IVA Responsable Inscripto")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(m_left + 10, m_top - 245, "Condición de venta: ")
        c.setFont("Helvetica", 9)
        c.drawString(m_left + 110, m_top - 245, "Cuenta Corriente")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 80, m_top - 200, "Apellido y Nombre / Razón Social: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 80, m_top - 200, cliente_nombre_display)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 30, m_top - 225, "Domicilio Comercial: ")
        c.setFont("Helvetica", 8)
        c.drawString(width/2 + 70, m_top - 225, domicilio_cliente)

        c.setFont("Helvetica-Bold", 9)
        c.drawString(width/2 - 18, m_top - 245, "Remito: ")
        c.setFont("Helvetica", 9)
        c.drawString(width/2 + 25, m_top - 245, remito_str)

        if datos_original:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.red)
            orig_pv = datos_original.get("punto_venta", 0)
            orig_nro = datos_original.get("nro_comprobante", 0)
            c.drawString(m_left + 10, m_top - 270,
                f"Fac. A: {orig_pv:05d}-{orig_nro:08d}")
            c.setFillColor(colors.black)

        y_grid_top = m_top - 310

        c.setFillColor(colors.lightgrey)
        c.rect(m_left, y_grid_top - 25, m_w, 25, fill=1, stroke=1)
        c.setFillColor(colors.black)

        c.setFont("Helvetica-Bold", 7)
        cx = [m_left, m_left + 35, m_left + 90, m_left + 230, m_left + 270, m_left + 310, m_left + 355, m_left + 395, m_left + 440, m_left + 490, m_right]

        c.drawString(cx[1]+5, y_grid_top - 15, "Código")
        c.drawString(cx[2]+5, y_grid_top - 15, "Producto / Servicio")
        c.drawCentredString((cx[3]+cx[4])/2, y_grid_top - 15, "Cantidad")
        c.drawCentredString((cx[4]+cx[5])/2, y_grid_top - 15, "U. medida")
        c.drawCentredString((cx[5]+cx[6])/2, y_grid_top - 15, "Precio Unit.")
        c.drawCentredString((cx[6]+cx[7])/2, y_grid_top - 15, "% Bonif")
        c.drawCentredString((cx[7]+cx[8])/2, y_grid_top - 15, "Subtotal")
        c.drawCentredString((cx[8]+cx[9])/2, y_grid_top - 12, "Alicuota")
        c.drawCentredString((cx[8]+cx[9])/2, y_grid_top - 21, "IVA")
        c.drawCentredString((cx[9]+cx[10])/2, y_grid_top - 15, "Subtotal c/IVA")

        c.rect(m_left, 250, m_w, y_grid_top - 275)

        y_row = y_grid_top - 40
        c.setFont("Helvetica", 8)
        productos_display = datos_factura.get("productos", [])
        if cliente_nombre != "Kilbel":
            productos_display = []
            for p in datos_factura.get("productos", []):
                cp = dict(p)
                cod = cp.get("codigo_arca", "")
                if cod == "105M":
                    cp["nombre"] = "105"
                elif cod == "104M":
                    cp["nombre"] = "104"
                productos_display.append(cp)

        for p in productos_display:
            bruto = p["cantidad"] * p["precio"]
            descuento = bruto * (bonif_pct / 100.0)
            subtotal_neto = bruto - descuento
            iva_item = subtotal_neto * 0.105
            subtotal_c_iva = subtotal_neto + iva_item

            c.drawString(cx[1] + 5, y_row, p.get("codigo_arca", ""))
            c.drawString(cx[2] + 5, y_row, p.get("nombre", "").lower())
            c.drawRightString(cx[4] - 5, y_row, fmt(p["cantidad"]))
            if p.get("es_kg", False):
                c.drawCentredString((cx[4]+cx[5])/2, y_row, "kilogramos")
            else:
                c.drawCentredString((cx[4]+cx[5])/2, y_row, "unidades")
            c.drawRightString(cx[6] - 5, y_row, fmt(p["precio"]))
            c.drawRightString(cx[7] - 5, y_row, fmt(bonif_pct))
            c.drawRightString(cx[8] - 5, y_row, fmt(subtotal_neto))
            c.drawCentredString((cx[8]+cx[9])/2, y_row, "10,5%")
            c.drawRightString(cx[10] - 5, y_row, fmt(subtotal_c_iva))
            y_row -= 15

        c.rect(m_left, 100, m_w, 150)
        c.setFont("Helvetica", 10)

        c.drawString(m_left + 100, 230, "Importe Otros Tributos: $")
        c.drawString(m_left + 230, 230, "0,00")

        c.setFont("Helvetica-Bold", 10)
        tx = width - 150
        vx = width - 35

        c.drawRightString(tx, 230, "Importe Neto Gravado: $")
        c.drawRightString(vx, 230, fmt(neto_total))

        c.drawRightString(tx, 215, "IVA 27%: $")
        c.drawRightString(vx, 215, "0,00")

        c.drawRightString(tx, 200, "IVA 21%: $")
        c.drawRightString(vx, 200, "0,00")

        c.drawRightString(tx, 185, "IVA 10.5%: $")
        c.drawRightString(vx, 185, fmt(iva_total))

        c.drawRightString(tx, 170, "IVA 5%: $")
        c.drawRightString(vx, 170, "0,00")

        c.drawRightString(tx, 155, "IVA 2.5%: $")
        c.drawRightString(vx, 155, "0,00")

        c.drawRightString(tx, 140, "IVA 0%: $")
        c.drawRightString(vx, 140, "0,00")

        c.drawRightString(tx, 125, "Importe Otros Tributos: $")
        c.drawRightString(vx, 125, "0,00")

        c.drawRightString(tx, 110, "Importe Total: $")
        c.drawRightString(vx, 110, fmt(total))

        c.setFont("Helvetica-Bold", 20)
        c.drawString(120, 75, "ARCA")

        c.setLineWidth(1)
        c.line(120, 70, 260, 70)

        c.setFont("Helvetica", 6)
        c.drawString(120, 62, "AGENCIA DE RECAUDACIÓN")
        c.drawString(120, 55, "Y CONTROL ADUANERO")

        c.setFont("Helvetica-Bold", 9)
        c.drawString(120, 35, "Comprobante Autorizado")
        c.setFont("Helvetica-BoldOblique", 7)
        c.drawString(120, 20, "Esta Agencia no se responsabiliza por los datos ingresados en el detalle de la operación")

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(width/2, 50, "Pág. 1/1")

        c.drawRightString(width - 150, 50, "CAE N°: ")
        c.setFont("Helvetica", 10)
        c.drawString(width - 145, 50, str(cae))

        vto_cae_str = str(vto_cae)
        if len(vto_cae_str) == 8:
            vto_cae_fmt = f"{vto_cae_str[6:8]}/{vto_cae_str[4:6]}/{vto_cae_str[0:4]}"
        else:
            vto_cae_fmt = vto_cae_str

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 150, 35, "Fecha de Vto. de CAE: ")
        c.setFont("Helvetica", 10)
        c.drawString(width - 145, 35, vto_cae_fmt)

        import base64
        try:
            fecha_qr = datetime.datetime.strptime(fecha_emision, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            fecha_qr = fecha_emision.replace('/', '-')

        qr_data = {
            "ver": 1,
            "fecha": fecha_qr,
            "cuit": 23257812634,
            "ptoVta": punto_venta,
            "tipoCmp": 3,
            "nroCmp": nro_comprobante,
            "importe": total,
            "moneda": "PES",
            "ctz": 1,
            "tipoDocRec": 80,
            "nroDocRec": int(cuit_cliente) if cuit_cliente else 0,
            "tipoCodAut": "E",
            "codAut": int(cae)
        }

        json_qr = json.dumps(qr_data)
        b64_qr = base64.b64encode(json_qr.encode('utf-8')).decode('utf-8')
        qr_url = f"https://servicioscf.afip.gob.ar/publico/comprobantes/cae.aspx?p={b64_qr}"

        img = qrcode.make(qr_url)
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        c.drawImage(ImageReader(qr_buffer), m_left + 5, 20, 75, 75)

        if idx < len(copias) - 1:
            c.showPage()

    c.save()
