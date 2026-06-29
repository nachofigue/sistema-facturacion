import os
import sys
from dotenv import load_dotenv

from gui import FacturaApp
from arca_bot import generar_factura

def main():
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(base_dir, '.env'))

    app = FacturaApp(start_bot_callback=generar_factura)
    app.mainloop()

if __name__ == "__main__":
    main()
