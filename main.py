import os
import sys
from dotenv import load_dotenv

from gui import FacturaApp
from arca_bot import generar_factura, generar_nota_credito

def main():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(base_dir, '.env'))

    import base_datos
    base_datos.crear_tablas()

    app = FacturaApp(
        start_bot_callback=generar_factura,
        start_nota_credito_callback=generar_nota_credito
    )
    app.mainloop()

if __name__ == "__main__":
    main()
