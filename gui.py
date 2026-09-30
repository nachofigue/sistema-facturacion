import customtkinter as ctk
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import shutil
import csv
from datetime import datetime
from PIL import Image
import tempfile
import urllib.request

APP_VERSION = "1.0.0"

class FacturaApp(ctk.CTk):
    def _init_pdf_cache(self):
        import os, json, sys
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self._pdf_cache_file = os.path.join(base_dir, "pdf_cache.json")
        self._pdf_cache = {}
        if os.path.exists(self._pdf_cache_file):
            try:
                with open(self._pdf_cache_file, "r", encoding="utf-8") as f:
                    self._pdf_cache = json.load(f)
            except:
                pass

    def _save_pdf_cache(self):
        import json
        try:
            with open(self._pdf_cache_file, "w", encoding="utf-8") as f:
                json.dump(self._pdf_cache, f)
        except:
            pass
    def __init__(self, start_bot_callback, start_nota_credito_callback=None):
        super().__init__()
        self._init_pdf_cache()
        
        self.start_bot_callback = start_bot_callback
        self.start_nota_credito_callback = start_nota_credito_callback
        
        # Configuración de ventana
        self.title("Automatización de Facturas - ARCA")
        self.after(10, lambda: self.state("zoomed"))
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # Cargar productos
        self.productos_config = self.load_config()
        self.product_entries = [] # Guardará (nombre, codigo, precio, entry_widget)
        
        self.current_sucursal_matches = []
        self.sucursales_tunel = [
            "Av Fray Cayetano Rodriguez 3845 - Santa Fe, Santa Fe",
            "9 De Julio 1838 - Santo Tome, Santa Fe",
            "Avellaneda 1902 - Santo Tome, Santa Fe",
            "San Martin 2998 - Santa Fe, Santa Fe",
            "Saavedra 3101 - Santa Fe, Santa Fe",
            "Avda General Lopez 3569 - Santa Fe, Santa Fe",
            "Estanislao Zeballos 3998 - Santa Fe, Santa Fe",
            "Colectora Oeste Ap Rosario Sta Fe Km 151 - Santo Tome, Santa Fe"
        ]

        self.sucursales_kilbel = [
            "Lopez Y Planes 4318 - Santa Fe, Santa Fe",
            "Ruta 1 Km 2.5 0 - Colastine, Santa Fe",
            "Avda. General Paz 7487 - Santa Fe, Santa Fe",
            "Uruguay 3101 - Santa Fe, Santa Fe",
            "San Jose 2629 - Santa Fe, Santa Fe",
            "Corrientes 2870 - Santa Fe, Santa Fe",
            "Urquiza 3300 - Santa Fe, Santa Fe",
            "Avda. Facundo Zuviria 6531 - Santa Fe, Santa Fe",
            "Balcarce 1167 - Santa Fe, Santa Fe",
            "Javier De La Rosa 241 - Santa Fe, Santa Fe",
            "Juan De Garay 3321 - Santa Fe, Santa Fe",
            "Remolcador Meteoro 2760 Piso:DIQII Dpto:25 - Santa Fe, Santa Fe"
        ]
        
        # Grid layout (2 columnas, 2 filas principales)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=3) # Formulario
        self.grid_rowconfigure(1, weight=1) # Logs
        
        self.modo_prueba = ctk.BooleanVar(value=False)
        self.setup_ui()
        
    def load_config(self):
        import sys
        import shutil
        # Si se ejecuta como .exe, toma la ruta del ejecutable o entorno temporal, sino la del script.
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            config_path = os.path.join(base_dir, "config.json")
            if not os.path.exists(config_path) and hasattr(sys, '_MEIPASS'):
                bundled_config = os.path.join(sys._MEIPASS, "config.json")
                if os.path.exists(bundled_config):
                    shutil.copy2(bundled_config, config_path)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("productos", []) if isinstance(data, dict) else data
        return []

    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="nsew")
        
        self.tab_facturacion = self.tabview.add("Facturación")
        self.tab_precios = self.tabview.add("Precios de Productos")
        self.tab_archivo = self.tabview.add("Archivo de Comprobantes")
        self.tab_estadisticas = self.tabview.add("Estadísticas")
        
        self.tab_facturacion.grid_columnconfigure(0, weight=1)
        self.tab_facturacion.grid_columnconfigure(1, weight=1)
        self.tab_facturacion.grid_rowconfigure(0, weight=1)
        
        # --- SECCIÓN A: Datos Generales (Columna 0) ---
        self.frame_general = ctk.CTkScrollableFrame(self.tab_facturacion)
        self.frame_general.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.frame_general, text="Datos del Remito", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Fecha del Remito
        ctk.CTkLabel(self.frame_general, text="Fecha del Remito (DD/MM/AAAA)").pack(anchor="w", padx=20)
        self.entry_fecha = ctk.CTkEntry(self.frame_general, placeholder_text="DD/MM/AAAA", border_width=2, border_color="#565656")
        self.entry_fecha.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_fecha.bind("<Return>", lambda e: self.focus_next_widget(self.entry_remito))
        self.entry_fecha.bind("<KeyRelease>", self.format_fecha)
        self.entry_fecha.bind("<FocusIn>", lambda e: self.entry_fecha.configure(border_color="#8ab4f8"))
        self.entry_fecha.bind("<FocusOut>", lambda e: self.entry_fecha.configure(border_color="#565656"))

        # Número de Orden
        ctk.CTkLabel(self.frame_general, text="Número de Orden").pack(anchor="w", padx=20)
        self.entry_orden = ctk.CTkEntry(self.frame_general, border_width=2, border_color="#565656")
        self.entry_orden.insert(0, "00002")
        vcmd_orden = (self.register(self._validate_only_digits), '%P', 5)
        self.entry_orden.configure(validate='key', validatecommand=vcmd_orden)
        self.entry_orden.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_orden.bind("<Return>", lambda e: self.focus_next_widget(self.entry_remito))
        self.entry_orden.bind("<Shift-Return>", lambda e: self.focus_next_widget(self.entry_fecha))
        self.entry_orden.bind("<FocusIn>", lambda e: self.entry_orden.configure(border_color="#8ab4f8"))
        self.entry_orden.bind("<FocusOut>", lambda e: self.entry_orden.configure(border_color="#565656"))
        
        # Número de Remito
        ctk.CTkLabel(self.frame_general, text="Número de Remito").pack(anchor="w", padx=20)
        self.entry_remito = ctk.CTkEntry(self.frame_general, border_width=2, border_color="#565656")
        self.entry_remito.insert(0, "0000")
        vcmd_remito = (self.register(self._validate_remito), '%P')
        self.entry_remito.configure(validate='key', validatecommand=vcmd_remito)
        self.entry_remito.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_remito.bind("<Return>", self.handle_remito_enter)
        self.entry_remito.bind("<Shift-Return>", lambda e: self.focus_next_widget(self.entry_fecha))
        self.entry_remito.bind("<FocusIn>", lambda e: self.entry_remito.configure(border_color="#8ab4f8"))
        self.entry_remito.bind("<FocusOut>", lambda e: self.handle_remito_focus_out(e))
        
        # Cliente (Dropdown)
        ctk.CTkLabel(self.frame_general, text="Cliente").pack(anchor="w", padx=20)
        self.combo_cliente = ctk.CTkComboBox(self.frame_general, values=["El Tunel S.A.", "Kilbel"], border_width=2, border_color="#565656")
        self.combo_cliente.pack(fill="x", padx=20, pady=(0, 15))
        # Bindear Enter en el combobox para autocompletar 'k' y 't'
        if hasattr(self.combo_cliente, "_entry"):
            c_entry = self.combo_cliente._entry
            c_entry.bind("<Return>", self.handle_cliente_enter)
            c_entry.bind("<Shift-Return>", lambda e: self.focus_next_widget(self.entry_remito))
            c_entry.configure(highlightthickness=2, highlightbackground="#565656", highlightcolor="#8ab4f8")
            vcmd_nodig = (self.register(self._validate_no_digits), '%P')
            c_entry.configure(validate='key', validatecommand=vcmd_nodig)
        else:
            self.combo_cliente.bind("<Return>", self.handle_cliente_enter)
            vcmd_nodig = (self.register(self._validate_no_digits), '%P')
            self.combo_cliente.configure(validate='key', validatecommand=vcmd_nodig)
        
        
        # Sucursal
        ctk.CTkLabel(self.frame_general, text="Sucursal del Supermercado").pack(anchor="w", padx=20)
        self.entry_sucursal = ctk.CTkEntry(self.frame_general, border_width=2, border_color="#565656")
        self.entry_sucursal.pack(fill="x", padx=20, pady=(0, 5))
        
        self.label_sucursal_match = ctk.CTkLabel(self.frame_general, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.label_sucursal_match.pack(anchor="w", padx=20, pady=(0, 15))
        self.entry_sucursal.bind("<KeyRelease>", self.on_sucursal_type)
        self.entry_sucursal.bind("<Shift-Return>", lambda e: self.focus_next_widget(self.combo_cliente))
        self.entry_sucursal.bind("<FocusIn>", lambda e: self.entry_sucursal.configure(border_color="#8ab4f8"))
        self.entry_sucursal.bind("<FocusOut>", lambda e: self.entry_sucursal.configure(border_color="#565656"))
        
        self.combo_cliente.set("")
        self.entry_sucursal.insert(0, "")
        
        # --- SECCIÓN B: Productos (Columna 1) ---
        self.frame_productos = ctk.CTkScrollableFrame(self.tab_facturacion, label_text="Cantidades por Producto")
        self.frame_productos.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        # Enlazar Enter de sucursal al primer producto
        if self.productos_config:
            # Crear los widgets primero
            for index, prod in enumerate(self.productos_config):
                ctk.CTkLabel(self.frame_productos, text=prod["nombre"].upper()).pack(anchor="w", padx=10, pady=(10, 0))
                entry = ctk.CTkEntry(self.frame_productos, placeholder_text="0", border_width=2, border_color="#565656")
                if index == 0:
                    entry.insert(0, "1") # DATO DE PRUEBA
                vcmd_qty = (self.register(self._validate_product_qty), '%P')
                entry.configure(validate='key', validatecommand=vcmd_qty)
                entry.pack(fill="x", padx=10, pady=(0, 5))
                entry.bind("<FocusIn>", lambda e, ent=entry: ent.configure(border_color="#8ab4f8"))
                entry.bind("<FocusOut>", lambda e, ent=entry: ent.configure(border_color="#565656"))
                self.product_entries.append({
                    "data": prod,
                    "widget": entry
                })
                
                # Separador visual para productos por kg
                if prod["codigo_arca"] == "PRO":
                    sep = ctk.CTkFrame(self.frame_productos, height=20, fg_color="transparent")
                    sep.pack(fill="x", padx=10, pady=(10, 0))
                    sep.pack_propagate(False)
                    ctk.CTkFrame(sep, height=2, fg_color="#555555").place(relx=0, rely=0.5, relwidth=0.42, anchor="w")
                    ctk.CTkLabel(sep, text="Kg", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray").place(relx=0.5, rely=0.5, anchor="center")
                    ctk.CTkFrame(sep, height=2, fg_color="#555555").place(relx=1, rely=0.5, relwidth=0.42, anchor="e")
            
            self.entry_sucursal.bind("<Return>", lambda e: self.handle_sucursal_enter(e, self.product_entries[0]["widget"]))
            
            # Enlazar Enter entre productos
            for i in range(len(self.product_entries)):
                current_entry = self.product_entries[i]["widget"]
                if i < len(self.product_entries) - 1:
                    next_entry = self.product_entries[i+1]["widget"]
                    # Default args in lambda for capturing 'next_entry' in loop
                    current_entry.bind("<Return>", lambda e, n=next_entry, c=current_entry: self.handle_product_enter(e, c, n))
                else:
                    current_entry.bind("<Return>", lambda e, c=current_entry: self.handle_product_enter(e, c, self.btn_generar))
                
                # Shift+Enter para ir al campo anterior
                if i > 0:
                    prev_entry = self.product_entries[i-1]["widget"]
                    current_entry.bind("<Shift-Return>", lambda e, p=prev_entry: self.handle_product_shift_enter(e, p))
                else:
                    current_entry.bind("<Shift-Return>", lambda e: self.handle_product_shift_enter(e, self.entry_sucursal))
        else:
            ctk.CTkLabel(self.frame_productos, text="No se encontraron productos en config.json").pack(pady=20)
            self.entry_sucursal.bind("<Return>", lambda e: self.handle_sucursal_enter(e, self.btn_generar))

        # Botón Generar
        self.btn_generar = ctk.CTkButton(self.frame_general, text="Ver vista previa de factura", height=40, font=ctk.CTkFont(size=15, weight="bold"), command=self.on_generar_click)
        self.btn_generar.pack(fill="x", padx=20, pady=30)
        self.btn_generar.bind("<Return>", lambda e: self.on_generar_click())

        # --- SECCIÓN LOGS (Fila 1, ocupa ambas columnas) ---
        self.frame_logs = ctk.CTkFrame(self)
        self.frame_logs.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        self.frame_logs.grid_columnconfigure(0, weight=1)
        self.frame_logs.grid_rowconfigure(0, weight=1)
        
        self.textbox_log = ctk.CTkTextbox(self.frame_logs, state="disabled", font=ctk.CTkFont(family="Consolas", size=12))
        self.textbox_log.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.log_message("Sistema iniciado. Presiona 'Enter' para navegar entre campos.")
        
        self.setup_precios_tab()
        self.setup_archivo_tab()
        self.setup_estadisticas_tab()
        
        self.console_visible = False
        self.frame_logs.grid_remove()
        self.switch_modo_prueba = ctk.CTkSwitch(
            self, text="Modo Prueba (sin ARCA)",
            variable=self.modo_prueba,
            onvalue=True, offvalue=False,
            command=self.on_modo_prueba_toggle,
            font=ctk.CTkFont(size=12)
        )
        self.switch_modo_prueba.place(relx=0.0, x=20, y=10, anchor="nw")

        self.btn_toggle_console = ctk.CTkButton(self, text="Mostrar Consola", width=120, height=28, command=self.toggle_console)
        self.btn_toggle_console.place(relx=0.98, y=15, anchor="ne")
        
        # Foco inicial
        self.entry_fecha.focus_set()

        # Comprobar actualizaciones
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def toggle_console(self):
        if self.console_visible:
            self.frame_logs.grid_remove()
            self.btn_toggle_console.configure(text="Mostrar Consola")
            self.console_visible = False
        else:
            self.frame_logs.grid()
            self.btn_toggle_console.configure(text="Ocultar Consola")
            self.console_visible = True

    def on_modo_prueba_toggle(self):
        if self.modo_prueba.get():
            self.btn_generar.configure(text="Ver vista previa (SIMULACIÓN)", fg_color="#e67e22")
        else:
            self.btn_generar.configure(text="Ver vista previa de factura", fg_color=("#3B8ED0", "#1F6AA5"))

    def setup_precios_tab(self):
        self.tab_precios.grid_columnconfigure(0, weight=1)
        self.tab_precios.grid_rowconfigure(0, weight=1)
        
        self.frame_precios = ctk.CTkScrollableFrame(self.tab_precios)
        self.frame_precios.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # Títulos de columnas
        header_frame = ctk.CTkFrame(self.frame_precios, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(header_frame, text="PRODUCTO", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="KILBEL", width=100, anchor="center", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=10)
        ctk.CTkLabel(header_frame, text="TUNEL", width=100, anchor="center", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=10)

        self.precio_entries = []
        if self.productos_config:
            for index, prod in enumerate(self.productos_config):
                row_frame = ctk.CTkFrame(self.frame_precios)
                row_frame.pack(fill="x", padx=10, pady=5)
                
                ctk.CTkLabel(row_frame, text=prod["nombre"].upper(), width=200, anchor="w").pack(side="left", padx=10)
                
                entry_kilbel = ctk.CTkEntry(row_frame, width=100, justify="center")
                entry_kilbel.insert(0, str(prod.get("precio_kilbel", prod.get("precio", 0))))
                entry_kilbel.pack(side="right", padx=10)

                entry_tunel = ctk.CTkEntry(row_frame, width=100, justify="center")
                entry_tunel.insert(0, str(prod.get("precio_tunel", prod.get("precio", 0))))
                entry_tunel.pack(side="right", padx=10)
                
                self.precio_entries.append({
                    "data": prod, 
                    "widget_tunel": entry_tunel,
                    "widget_kilbel": entry_kilbel
                })
                
        self.btn_guardar_precios = ctk.CTkButton(self.tab_precios, text="Guardar Cambios", command=self.guardar_precios)
        self.btn_guardar_precios.grid(row=1, column=0, pady=10, padx=(0, 10))

        self.btn_pdf_precios = ctk.CTkButton(self.tab_precios, text="Generar PDF de Precios", command=self.generar_pdf_precios)
        self.btn_pdf_precios.grid(row=1, column=1, pady=10, padx=(10, 0))

    def setup_archivo_tab(self):
        self._node_paths = {}
        self._carpeta_paths = {}
        self.tab_archivo.grid_columnconfigure(0, weight=1)
        self.tab_archivo.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self.tab_archivo)
        main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        # --- Top bar: cliente + fecha ---
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        top_frame.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(top_frame, text="Cliente:").grid(row=0, column=0, padx=5, pady=5)
        self.combo_archivo_cliente = ctk.CTkComboBox(top_frame, values=["-", "El Tunel S.A.", "Kilbel"], command=self.on_archivo_cliente_change)
        self.combo_archivo_cliente.set("-")
        self.combo_archivo_cliente.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(top_frame, text="F. Facturación:").grid(row=0, column=2, padx=(5, 5), pady=5)
        self.combo_archivo_fecha = ctk.CTkComboBox(top_frame, values=[], command=self.on_archivo_fecha_change, width=110)
        self.combo_archivo_fecha.grid(row=0, column=3, padx=5, pady=5)
        self.combo_archivo_fecha.set("")
        self.combo_archivo_fecha.configure(state="disabled")

        ctk.CTkLabel(top_frame, text="F. Remito:").grid(row=0, column=4, padx=(10, 5), pady=5)
        self.combo_archivo_remito = ctk.CTkComboBox(top_frame, values=[], command=self.on_archivo_remito_change, width=110)
        self.combo_archivo_remito.grid(row=0, column=5, padx=5, pady=5)
        self.combo_archivo_remito.set("")
        self.combo_archivo_remito.configure(state="disabled")

        btn_refresh = ctk.CTkButton(top_frame, text="Refrescar", width=80, command=self.refresh_archivo_tree)
        btn_refresh.grid(row=0, column=6, padx=(10, 5), pady=5)

        ctk.CTkLabel(top_frame, text="Orden:").grid(row=0, column=7, padx=(10, 5), pady=5)
        self.combo_archivo_orden = ctk.CTkComboBox(top_frame, values=["Nro Mayor a Menor", "Nro Menor a Mayor", "Por Supermercado", "Por Fecha de Remito"], command=self.on_archivo_orden_change, width=130)
        self.combo_archivo_orden.set("Nro Mayor a Menor")
        self.combo_archivo_orden.grid(row=0, column=8, padx=5, pady=5)

        # --- Treeview ---
        tree_frame = ctk.CTkFrame(main_frame)
        tree_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=30, font=("Segoe UI", 12), indent=40)
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="white", font=("Segoe UI", 12, "bold"))

        self.archivo_tree = ttk.Treeview(tree_frame, columns=("f_remito", "f_facturacion", "total", "size", "cliente"), show="tree", selectmode="browse")
        self.archivo_tree.grid(row=0, column=0, sticky="nsew")
        self.archivo_tree.column("#0", width=300)
        self.archivo_tree.column("f_remito", width=90, anchor="center")
        self.archivo_tree.column("f_facturacion", width=90, anchor="center")
        self.archivo_tree.column("total", width=100, anchor="e")
        self.archivo_tree.column("size", width=65, anchor="e")
        self.archivo_tree.column("cliente", width=70, anchor="center")
        self.archivo_tree.heading("#0", text="Nombre")
        self.archivo_tree.heading("f_remito", text="F. Remito")
        self.archivo_tree.heading("f_facturacion", text="F. Facturación")
        self.archivo_tree.heading("total", text="Total")
        self.archivo_tree.heading("size", text="Tamaño")
        self.archivo_tree.heading("cliente", text="Cliente")

        scroll_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=self.archivo_tree.yview)
        scroll_tree.grid(row=0, column=1, sticky="ns")
        self.archivo_tree.configure(yscrollcommand=scroll_tree.set)
        self.archivo_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.archivo_tree.bind("<Double-1>", self.on_tree_double_click)

        # --- Botones de acción ---
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.btn_copiar_pdfs = ctk.CTkButton(btn_frame, text="Copiar PDFs", command=self.copiar_pdfs_seleccionados, state="disabled")
        self.btn_copiar_pdfs.pack(side="left", padx=10)

        self.btn_abrir_excel = ctk.CTkButton(btn_frame, text="Abrir Excel", command=self.abrir_excel_facturas, state="disabled")
        self.btn_abrir_excel.pack(side="left", padx=10)

        self.btn_listar_precios = ctk.CTkButton(btn_frame, text="Listar Totales", command=self.listar_precios_carpeta, state="disabled")
        self.btn_listar_precios.pack(side="left", padx=10)

        self.btn_copiar_nros = ctk.CTkButton(btn_frame, text="Copiar Nro de Comprobante", command=self.copiar_nros_comprobante, state="disabled", fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_copiar_nros.pack(side="left", padx=10)

        self.btn_copiar_totales = ctk.CTkButton(btn_frame, text="Copiar Totales", command=self.copiar_totales_precios, state="disabled", fg_color="#2e7d32", hover_color="#1b5e20")
        self.btn_copiar_totales.pack(side="left", padx=10)

        self.btn_eliminar_pdf = ctk.CTkButton(btn_frame, text="Eliminar", command=self.eliminar_pdf_seleccionado, state="disabled", fg_color="#c0392b", hover_color="#96281b")
        self.btn_eliminar_pdf.pack(side="left", padx=10)

        self.btn_reporte_diario = ctk.CTkButton(
            btn_frame, text="Reporte Diario",
            command=self.generar_reporte_diario,
            fg_color="#1565C0", hover_color="#0D47A1",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_reporte_diario.pack(side="left", padx=10)

        sep_frame = ctk.CTkFrame(btn_frame, width=2, fg_color="#555555")
        sep_frame.pack(side="left", padx=5, fill="y", pady=5)

        self.btn_nota_credito = ctk.CTkButton(
            btn_frame, text="Generar Nota de Crédito",
            command=self.on_generar_nota_credito,
            state="disabled",
            fg_color="#7D3C98", hover_color="#5B2C6F",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_nota_credito.pack(side="left", padx=10)

        self._datos_precios = None

        # Inicializar el tree con lo que haya
        self.refresh_archivo_tree()

    def setup_estadisticas_tab(self):
        self.tab_estadisticas.grid_columnconfigure(0, weight=1)
        self.tab_estadisticas.grid_rowconfigure(1, weight=1)

        # Filtros
        frame_filtros = ctk.CTkFrame(self.tab_estadisticas)
        frame_filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(frame_filtros, text="Sucursal:").pack(side="left", padx=5)
        todas_sucursales = ["Todas"] + self.sucursales_tunel + self.sucursales_kilbel
        self.combo_est_sucursal = ctk.CTkComboBox(frame_filtros, values=todas_sucursales, width=300)
        self.combo_est_sucursal.pack(side="left", padx=5)

        import datetime
        hoy = datetime.date.today()
        hace_4_semanas = hoy - datetime.timedelta(days=28)

        ctk.CTkLabel(frame_filtros, text="Desde (DD/MM/YYYY):").pack(side="left", padx=5)
        self.entry_est_desde = ctk.CTkEntry(frame_filtros, width=100)
        self.entry_est_desde.pack(side="left", padx=5)
        self.entry_est_desde.insert(0, hace_4_semanas.strftime("%d/%m/%Y"))

        ctk.CTkLabel(frame_filtros, text="Hasta:").pack(side="left", padx=5)
        self.entry_est_hasta = ctk.CTkEntry(frame_filtros, width=100)
        self.entry_est_hasta.pack(side="left", padx=5)
        self.entry_est_hasta.insert(0, hoy.strftime("%d/%m/%Y"))

        btn_actualizar = ctk.CTkButton(frame_filtros, text="Actualizar Gráfico", command=self.actualizar_estadisticas)
        btn_actualizar.pack(side="left", padx=15)

        # Gráfico
        self.canvas_estadisticas = tk.Canvas(self.tab_estadisticas, bg="#2b2b2b", highlightthickness=0)
        self.canvas_estadisticas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def actualizar_estadisticas(self):
        import base_datos
        from datetime import datetime, timedelta
        
        sucursal = self.combo_est_sucursal.get()
        desde_str = self.entry_est_desde.get()
        hasta_str = self.entry_est_hasta.get()
        
        try:
            desde_dt = datetime.strptime(desde_str, "%d/%m/%Y")
            hasta_dt = datetime.strptime(hasta_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Error", "Formato de fecha inválido. Usa DD/MM/YYYY")
            return
            
        desde_bd = desde_dt.strftime("%Y-%m-%d")
        hasta_bd = hasta_dt.strftime("%Y-%m-%d")
        
        # Limpiar canvas
        self.canvas_estadisticas.delete("all")
        
        # Obtener ventas
        if sucursal == "Todas":
            ventas = []
            for suc in self.sucursales_tunel + self.sucursales_kilbel:
                ventas.extend(base_datos.obtener_ventas_por_sucursal(suc, desde_bd, hasta_bd))
        else:
            ventas = base_datos.obtener_ventas_por_sucursal(sucursal, desde_bd, hasta_bd)
            
        if not ventas:
            self.canvas_estadisticas.create_text(400, 200, text="No hay ventas registradas en este período.", fill="white", font=("Arial", 16))
            return
            
        # Agrupar por semana
        semanas = {}
        for fecha_str, total in ventas:
            f = datetime.strptime(fecha_str, "%Y-%m-%d")
            # Obtenemos el inicio de la semana (Lunes) y el final (Domingo)
            inicio_semana = f - timedelta(days=f.weekday())
            semanas[inicio_semana] = semanas.get(inicio_semana, 0) + total
            
        # Dibujar gráfico de barras
        if not semanas:
            return
            
        self.canvas_estadisticas.update()
        c_width = self.canvas_estadisticas.winfo_width()
        c_height = self.canvas_estadisticas.winfo_height()
        if c_width <= 1: c_width = 800
        if c_height <= 1: c_height = 400
        
        max_val = max(semanas.values())
        if max_val == 0: max_val = 1
        
        margin_bottom = 50
        margin_top = 30
        margin_left = 60
        margin_right = 20
        
        # Dibujar Ejes
        self.canvas_estadisticas.create_line(margin_left, margin_top, margin_left, c_height - margin_bottom, fill="white")
        self.canvas_estadisticas.create_line(margin_left, c_height - margin_bottom, c_width - margin_right, c_height - margin_bottom, fill="white")
        
        # Dibujar valores de eje Y
        pasos_y = 5
        for i in range(pasos_y + 1):
            val = max_val * (i / pasos_y)
            y_pos = (c_height - margin_bottom) - (i / pasos_y) * (c_height - margin_bottom - margin_top)
            self.canvas_estadisticas.create_text(margin_left - 10, y_pos, text=f"${val:,.0f}", fill="white", anchor="e", font=("Arial", 9))
            
        n_barras = len(semanas)
        espacio_total = (c_width - margin_left - margin_right)
        ancho_barra = min(espacio_total / (n_barras * 1.5), 80)
        espacio_entre = (espacio_total - (ancho_barra * n_barras)) / (n_barras + 1)
        
        # Dibujar barras
        x_actual = margin_left + espacio_entre
        for inicio_semana, val in sorted(semanas.items()):
            fin_semana = inicio_semana + timedelta(days=6)
            sem = f"{inicio_semana.strftime('%d/%m')}\n-\n{fin_semana.strftime('%d/%m')}"
            altura_barra = (val / max_val) * (c_height - margin_bottom - margin_top)
            y1 = c_height - margin_bottom
            y2 = y1 - altura_barra
            x1 = x_actual
            x2 = x_actual + ancho_barra
            
            self.canvas_estadisticas.create_rectangle(x1, y2, x2, y1, fill="#1f538d", outline="#14375e")
            self.canvas_estadisticas.create_text(x1 + ancho_barra/2, y1 + 22, text=sem, fill="white", font=("Arial", 10), justify="center")
            self.canvas_estadisticas.create_text(x1 + ancho_barra/2, y2 - 10, text=f"${val:,.0f}", fill="white", font=("Arial", 9))
            
            x_actual += ancho_barra + espacio_entre

    def _deshabilitar_botones(self):
        self.btn_copiar_pdfs.configure(state="disabled")
        self.btn_abrir_excel.configure(state="disabled")
        self.btn_listar_precios.configure(state="disabled")
        self.btn_copiar_nros.configure(state="disabled")
        self.btn_copiar_totales.configure(state="disabled")
        self.btn_eliminar_pdf.configure(state="disabled")
        self.btn_nota_credito.configure(state="disabled")
        self._datos_precios = None

    def on_archivo_remito_change(self, choice):
        self.refresh_archivo_tree()

    def on_archivo_cliente_change(self, choice):
        self.combo_archivo_fecha.configure(values=[])
        self.combo_archivo_fecha.set("")
        self.combo_archivo_fecha.configure(state="disabled")
        self._deshabilitar_botones()
        self.refresh_archivo_tree()

    def on_archivo_fecha_change(self, choice):
        self.refresh_archivo_tree()

    def on_archivo_orden_change(self, choice):
        self.refresh_archivo_tree()

    def on_tree_select(self, event):
        self._save_pdf_cache()
        self._actualizar_botones()

    def on_tree_double_click(self, event):
        sel = self.archivo_tree.selection()
        if not sel:
            return
        item = sel[0]
        texto = self.archivo_tree.item(item, "text")
        if " | " in texto:
            texto = texto.split(" | ")[0].strip()
        if not texto.lower().endswith(".pdf"):
            return
        
        ruta = getattr(self, "_node_paths", {}).get(item)
        if ruta and os.path.isfile(ruta):
            os.startfile(ruta)

    def _get_pdf_seleccionado(self):
        sel = self.archivo_tree.selection()
        if not sel:
            return None
        item = sel[0]
        texto = self.archivo_tree.item(item, "text")
        if " | " in texto:
            texto = texto.split(" | ")[0].strip()
        if not texto.lower().endswith(".pdf"):
            return None
            
        ruta = getattr(self, "_node_paths", {}).get(item)
        if ruta and os.path.isfile(ruta):
            return ruta
        return None

    def _actualizar_botones(self):
        ruta = self._get_carpeta_seleccionada()
        estado = "normal" if ruta else "disabled"
        self.btn_copiar_pdfs.configure(state=estado)
        self.btn_abrir_excel.configure(state=estado)
        self.btn_listar_precios.configure(state=estado)
        estado_precios = "normal" if self._datos_precios else "disabled"
        self.btn_copiar_nros.configure(state=estado_precios)
        self.btn_copiar_totales.configure(state=estado_precios)
        estado_eliminar = "normal" if self._get_pdf_seleccionado() else "disabled"
        self.btn_eliminar_pdf.configure(state=estado_eliminar)
        estado_nc = "normal" if self._get_pdf_seleccionado() else "disabled"
        self.btn_nota_credito.configure(state=estado_nc)

    def refresh_archivo_tree(self):
        self._node_paths.clear()
        self._carpeta_paths.clear()

        for item in self.archivo_tree.get_children():
            self.archivo_tree.delete(item)

        self.archivo_tree.tag_configure("TUNEL", foreground="#e74c3c")
        self.archivo_tree.tag_configure("KILBEL", foreground="#2ecc71")
        self.archivo_tree.tag_configure("TUNEL_NC", foreground="#ff4444")
        self.archivo_tree.tag_configure("KILBEL_NC", foreground="#2ecc71")

        import os, json
        from datetime import datetime
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        base_path = os.path.join(desktop, "facturas")

        if not os.path.exists(base_path):
            self.archivo_tree.insert("", "end", text="No hay carpeta 'facturas' en el escritorio", iid="root_info")
            self._deshabilitar_botones()
            return

        cliente = self.combo_archivo_cliente.get()
        fecha_fact = self.combo_archivo_fecha.get()
        fecha_rem = getattr(self, "combo_archivo_remito", None)
        fecha_rem_val = fecha_rem.get() if fecha_rem else ""
        orden = self.combo_archivo_orden.get()

        all_data = {}
        todas_las_fechas_fact = set()
        todas_las_fechas_rem = set()
        
        for carpeta_cliente in os.listdir(base_path):
            ruta_cliente = os.path.join(base_path, carpeta_cliente)
            if not os.path.isdir(ruta_cliente):
                continue
            
            cliente_key = carpeta_cliente
            all_data[cliente_key] = {}
            
            for carpeta_fecha in os.listdir(ruta_cliente):
                ruta_fecha = os.path.join(ruta_cliente, carpeta_fecha)
                if not os.path.isdir(ruta_fecha):
                    continue
                
                todas_las_fechas_rem.add(carpeta_fecha)
                if carpeta_fecha not in all_data[cliente_key]:
                    all_data[cliente_key][carpeta_fecha] = []
                
                all_pdfs = [f for f in os.listdir(ruta_fecha) if f.lower().endswith(".pdf")]
                factura_pdfs = [f for f in all_pdfs if f.startswith("Factura_")]
                nc_pdfs = [f for f in all_pdfs if f.startswith("Nota_Credito_")]

                nc_map = {}
                for nc_pdf in nc_pdfs:
                    ruta_nc = os.path.join(ruta_fecha, nc_pdf)
                    orig_pv, orig_nro = self._extraer_factura_original_desde_nc(ruta_nc)
                    if orig_nro:
                        nc_total = self._extraer_total_pdf(ruta_nc)
                        nc_self_nro = nc_pdf.split("_")[-1].replace(".pdf", "")
                        nc_map[orig_nro] = (nc_self_nro, nc_total)

                metadatos_path = os.path.join(ruta_fecha, "metadatos.json")
                metadatos = {}
                if os.path.exists(metadatos_path):
                    try:
                        with open(metadatos_path, "r", encoding="utf-8") as f:
                            metadatos = json.load(f)
                    except Exception:
                        pass
                for pdf in factura_pdfs:
                    fecha_facturacion_str = metadatos.get(pdf, carpeta_fecha)
                    
                    try:
                        if len(carpeta_fecha.split("-")[-1]) == 2:
                            fecha_dt = datetime.strptime(carpeta_fecha, "%d-%m-%y")
                            fecha_remito_str = fecha_dt.strftime("%d-%m-%Y")
                        else:
                            fecha_dt = datetime.strptime(carpeta_fecha, "%d-%m-%Y")
                            fecha_remito_str = carpeta_fecha
                    except Exception:
                        fecha_dt = datetime.min
                        fecha_remito_str = carpeta_fecha
                        
                    todas_las_fechas_fact.add(fecha_facturacion_str)
                    
                    ruta_pdf = os.path.join(ruta_fecha, pdf)
                    size = os.path.getsize(ruta_pdf)
                    size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
                    
                    nro_factura = int(pdf.split("_")[-1].replace(".pdf", ""))
                    total = self._extraer_total_pdf(ruta_pdf)
                    total_str = f"${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if total else ""
                    
                    etiqueta = "TUNEL" if "tunel" in cliente_key.lower() else "KILBEL"
                    etiqueta_nc = "TUNEL_NC" if "tunel" in cliente_key.lower() else "KILBEL_NC"
                    
                    txt = pdf
                    tag_a_usar = etiqueta
                    if nro_factura in nc_map:
                        nc_nro, nc_total = nc_map[nro_factura]
                        nc_str = f"${nc_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if nc_total else ""
                        txt = f"{pdf}  |  NC: {nc_nro}  {nc_str}"
                        tag_a_usar = etiqueta_nc
                    
                    pdf_info = (str(nro_factura), etiqueta, txt, size_str, total_str, ruta_pdf, tag_a_usar, fecha_dt, ruta_fecha, fecha_remito_str, fecha_facturacion_str)
                    all_data[cliente_key][carpeta_fecha].append(pdf_info)

        def parse_date(d_str):
            try:
                from datetime import datetime
                return datetime.strptime(d_str, "%d-%m-%Y")
            except:
                from datetime import datetime
                return datetime.min

        fechas_fact_ordenadas = sorted(list(todas_las_fechas_fact), key=parse_date, reverse=True)
        fechas_rem_ordenadas = ["- Todos -"] + sorted(list(todas_las_fechas_rem), key=parse_date, reverse=True)

        self.combo_archivo_fecha.configure(values=["- Todos -"] + fechas_fact_ordenadas)
        self.combo_archivo_fecha.configure(state="normal" if fechas_fact_ordenadas else "disabled")
        if not fecha_fact:
            self.combo_archivo_fecha.set("- Todos -")
            fecha_fact = "- Todos -"

        if hasattr(self, "combo_archivo_remito"):
            self.combo_archivo_remito.configure(values=fechas_rem_ordenadas)
            self.combo_archivo_remito.configure(state="normal" if fechas_rem_ordenadas else "disabled")
            if not fecha_rem_val:
                self.combo_archivo_remito.set("- Todos -")
                fecha_rem_val = "- Todos -"

        # Combine items for flat view if specific filters are set
        if cliente == "-" and (fecha_fact != "- Todos -" or fecha_rem_val != "- Todos -"):
            items_planos = []
            for c_key, c_dates in all_data.items():
                for f_rem_key, pdfs in c_dates.items():
                    if fecha_rem_val != "- Todos -" and f_rem_key != fecha_rem_val:
                        continue
                    for pdf_info in pdfs:
                        if fecha_fact != "- Todos -" and pdf_info[10] != fecha_fact:
                            continue
                        items_planos.append(pdf_info)
            
            if not items_planos:
                self.archivo_tree.insert("", "end", text="No hay facturas con esos filtros")
                self._deshabilitar_botones()
                return
            
            if orden == "Nro Mayor a Menor":
                items_planos.sort(key=lambda x: int(x[0]), reverse=True)
            elif orden == "Nro Menor a Mayor":
                items_planos.sort(key=lambda x: int(x[0]))
            elif orden == "Por Supermercado":
                items_planos.sort(key=lambda x: (x[1], int(x[0])))
            elif orden == "Por Fecha de Remito":
                items_planos.sort(key=lambda x: (x[7], int(x[0])), reverse=True)

            txt_nodo = f"Resultados Filtro"
            fecha_id = self.archivo_tree.insert("", "end", text=txt_nodo, open=True)
            
            if items_planos:
                self._carpeta_paths[fecha_id] = items_planos[0][8]

            for nro, etiqueta, txt, size_str, total_str, ruta_pdf, tag, fecha_dt, ruta_fecha, f_rem, f_fact in items_planos:
                node_id = self.archivo_tree.insert(fecha_id, "end", text=txt, values=(f_rem, f_fact, total_str, size_str, etiqueta), tags=(tag,))
                self._node_paths[node_id] = ruta_pdf
            
            self._save_pdf_cache()
            self._actualizar_botones()
            return
            
        # Normal view by client (grouped by F. Facturación)
        for c_key in sorted(all_data.keys()):
            cliente_folder = "kilbel" if "kilbel" in c_key.lower() else "tunel"
            if cliente not in ("-", "") and cliente_folder != ("kilbel" if cliente == "Kilbel" else "tunel"):
                continue
            
            cliente_id = self.archivo_tree.insert("", "end", text=c_key.upper(), open=True)
            
            c_dates_sorted = sorted(all_data[c_key].keys(), key=parse_date, reverse=True)
            
            for d_key in c_dates_sorted:
                if fecha_rem_val != "- Todos -" and d_key != fecha_rem_val:
                    continue
                
                # Filter pdfs inside this delivery date by Facturacion
                factura_pdfs = [p for p in all_data[c_key][d_key] if (fecha_fact == "- Todos -" or p[10] == fecha_fact)]
                
                # If filter empties the folder, skip it unless no filters are applied
                if not factura_pdfs and fecha_fact != "- Todos -":
                    continue
                
                fecha_id = self.archivo_tree.insert(cliente_id, "end", text=d_key, open=False)
                
                if orden == "Nro Mayor a Menor":
                    factura_pdfs.sort(key=lambda x: int(x[0]), reverse=True)
                elif orden == "Nro Menor a Mayor":
                    factura_pdfs.sort(key=lambda x: int(x[0]))
                elif orden == "Por Fecha de Remito":
                    factura_pdfs.sort(key=lambda x: (x[7], int(x[0])), reverse=True)
                
                if not factura_pdfs:
                    self.archivo_tree.insert(fecha_id, "end", text="(sin archivos)")
                else:
                    self._carpeta_paths[fecha_id] = factura_pdfs[0][8]

                for nro, etiqueta, txt, size_str, total_str, ruta_pdf, tag, fecha_dt, ruta_fecha, f_rem, f_fact in factura_pdfs:
                    node_id = self.archivo_tree.insert(fecha_id, "end", text=txt, values=(f_rem, f_fact, total_str, size_str, etiqueta), tags=(tag,))
                    self._node_paths[node_id] = ruta_pdf
                    
        self._save_pdf_cache()
        self._actualizar_botones()

    def _get_carpeta_seleccionada(self):
        sel = self.archivo_tree.selection()
        if not sel:
            return None
        item = sel[0]
        return getattr(self, "_carpeta_paths", {}).get(item)
        item = sel[0]
        padres = []
        while item:
            texto = self.archivo_tree.item(item, "text")
            padres.insert(0, texto)
            item = self.archivo_tree.parent(item)

        # Vista combinada: seleccionar la carpeta "Facturas del {fecha}" (1 nivel)
        if len(padres) == 1 and padres[0].startswith("Facturas del "):
            fecha_texto = padres[0].replace("Facturas del ", "")
            base = os.path.join(os.path.expanduser("~"), "Desktop", "facturas")
            for carpeta_cliente in os.listdir(base):
                ruta = os.path.join(base, carpeta_cliente, fecha_texto)
                if os.path.isdir(ruta):
                    return ruta
            return None

        # Vista normal: cliente/fecha (2 niveles)
        if len(padres) == 2:
            cliente_texto = padres[0]
            fecha_texto = padres[1]
            if cliente_texto == "TUNEL":
                cliente_folder = "tunel"
            elif cliente_texto == "KILBEL":
                cliente_folder = "kilbel"
            else:
                return None
            ruta = os.path.join(os.path.expanduser("~"), "Desktop", "facturas", cliente_folder, fecha_texto)
            return ruta if os.path.isdir(ruta) else None

        return None

    def copiar_pdfs_seleccionados(self):
        ruta = self._get_carpeta_seleccionada()
        if not ruta:
            return
        pdfs = [f for f in os.listdir(ruta) if f.lower().endswith(".pdf")]
        if not pdfs:
            self.log_message("No hay PDFs en la carpeta seleccionada.")
            return
        # Copiar al portapapeles con PowerShell (Get-ChildItem | Set-Clipboard)
        import subprocess
        ps_cmd = f'Get-ChildItem -Path "{ruta}" -Filter "*.pdf" | Set-Clipboard'
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        self.log_message(f"{len(pdfs)} PDF(s) copiados al portapapeles. Presioná Ctrl+V para pegarlos.")

    def abrir_excel_facturas(self):
        ruta = self._get_carpeta_seleccionada()
        if not ruta:
            return
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_csv = os.path.join(os.path.expanduser("~"), "Desktop", f"facturas_{fecha_actual}.csv")
        pdfs = [f for f in os.listdir(ruta) if f.lower().endswith(".pdf")]
        if not pdfs:
            self.log_message("No hay PDFs en la carpeta seleccionada.")
            return
        pdfs.sort()
        with open(archivo_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Archivo", "Tamaño (KB)", "Ruta completa"])
            for pdf in pdfs:
                ruta_pdf = os.path.join(ruta, pdf)
                size_kb = round(os.path.getsize(ruta_pdf) / 1024, 2)
                writer.writerow([pdf, size_kb, ruta_pdf])
        os.startfile(archivo_csv)
        self.log_message(f"Excel generado: {archivo_csv}")

    def _extraer_total_pdf(self, ruta_pdf):
        import os
        cache_key = str(ruta_pdf)
        if cache_key in self._pdf_cache and "total" in self._pdf_cache[cache_key]:
            return self._pdf_cache[cache_key]["total"]
        
        total = None
        try:
            from pypdf import PdfReader
            reader = PdfReader(ruta_pdf)
            for page in reader.pages:
                texto = page.extract_text()
                lineas = texto.split("\n")
                for i, linea in enumerate(lineas):
                    if "Importe Total:" in linea:
                        parte = ""
                        if "$" in linea:
                            tras_dolar = linea.split("$")[-1].strip()
                            if tras_dolar:
                                parte = tras_dolar
                        if not parte and i + 1 < len(lineas):
                            parte = lineas[i + 1].strip()
                        if parte:
                            total = float(parte.replace(",", "."))
                            break
                if total is not None:
                    break
        except Exception:
            pass
            
        if cache_key not in self._pdf_cache:
            self._pdf_cache[cache_key] = {}
        self._pdf_cache[cache_key]["total"] = total
        return total

    def _extraer_factura_original_desde_nc(self, ruta_pdf):
        import re
        from pypdf import PdfReader
        try:
            reader = PdfReader(ruta_pdf)
            texto_completo = ""
            for page in reader.pages:
                texto_completo += page.extract_text() + "\n"
            match = re.search(r'Fac\.\s*A\s*:\s*(\d{5})-(\d{8})', texto_completo)
            if match:
                return int(match.group(1)), int(match.group(2))
        except:
            pass
        return None, None

    def _extraer_datos_desde_pdf(self, ruta_pdf):
        import re
        from pypdf import PdfReader
        datos = {}

        filename = os.path.basename(ruta_pdf)
        match = re.search(r'_(\d{5})_(\d{8})\.pdf$', filename)
        if match:
            datos["punto_venta_original"] = int(match.group(1))
            datos["nro_comprobante_original"] = int(match.group(2))

        ruta = os.path.dirname(ruta_pdf)
        if "kilbel" in ruta.lower():
            datos["cliente_nombre"] = "Kilbel"
            datos["cuit_cliente"] = "30681989567"
        elif "tunel" in ruta.lower():
            datos["cliente_nombre"] = "El Tunel S.A."
            datos["cuit_cliente"] = "30518084557"

        carpeta_fecha = os.path.basename(ruta)
        if carpeta_fecha:
            try:
                partes = carpeta_fecha.split("-")
                datos["fecha"] = f"{partes[0]}/{partes[1]}/{partes[2]}"
            except Exception:
                datos["fecha"] = carpeta_fecha

        total = self._extraer_total_pdf(ruta_pdf)
        if total:
            datos["imp_total"] = total
            datos["imp_neto"] = round(total / 1.105, 2)
            datos["imp_iva"] = round(total - datos["imp_neto"], 2)

        try:
            reader = PdfReader(ruta_pdf)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()
            lineas = texto.split("\n")

            for i, linea in enumerate(lineas):
                if "CAE" in linea:
                    m = re.search(r'(\d{14})', linea)
                    if m:
                        datos["cae_original"] = m.group(1)
                    elif i + 1 < len(lineas):
                        m2 = re.search(r'(\d{14})', lineas[i + 1])
                        if m2:
                            datos["cae_original"] = m2.group(1)
                    if datos.get("cae_original"):
                        break

            for i, linea in enumerate(lineas):
                if "Remito:" in linea:
                    rem_str = linea.split("Remito:")[-1].strip()
                    if not rem_str and i + 1 < len(lineas):
                        rem_str = lineas[i + 1].strip()
                    if "-" in rem_str:
                        parts = rem_str.split("-")
                        datos["orden"] = parts[0]
                        try:
                            datos["remito"] = int(parts[1].split()[0])
                        except:
                            pass
                    else:
                        try:
                            datos["remito"] = int(rem_str.split()[0])
                        except:
                            pass
                    break

            ultimo_domicilio = -1
            for i, linea in enumerate(lineas):
                if "Domicilio Comercial" in linea:
                    ultimo_domicilio = i
            if ultimo_domicilio >= 0 and ultimo_domicilio + 1 < len(lineas):
                suc_val = lineas[ultimo_domicilio].split("Domicilio Comercial")[-1]
                if ":" in suc_val:
                    suc_val = suc_val.split(":")[-1].strip()
                if not suc_val:
                    suc_val = lineas[ultimo_domicilio + 1].strip()
                if suc_val:
                    datos["sucursal"] = suc_val

            datos["productos"] = []
            inicio_productos = -1
            for i, linea in enumerate(lineas):
                if "Subtotal c/IVA" in linea or "Subtotal c/IVA" in linea:
                    inicio_productos = i + 1
                    break

            if inicio_productos > 0:
                fin_productos = -1
                for i in range(inicio_productos, len(lineas)):
                    if "Importe" in lineas[i] and ("Tributos" in lineas[i] or "Neto" in lineas[i] or "Total" in lineas[i]):
                        fin_productos = i
                        break
                if fin_productos == -1:
                    fin_productos = len(lineas)

                lineas_productos = lineas[inicio_productos:fin_productos]
                for j in range(0, len(lineas_productos) - 7, 8):
                    bloque = lineas_productos[j:j+8]
                    if len(bloque) < 8:
                        break
                    nombre = bloque[0].strip().lower()
                    if not nombre or nombre in ("importe neto gravado", "importe otros tributos"):
                        continue
                    try:
                        cantidad_str = bloque[1].strip().replace(",", ".")
                        cantidad = float(cantidad_str)
                        unidad = bloque[2].strip().lower()
                        precio_str = bloque[3].strip().replace(",", ".")
                        precio = float(precio_str)
                        es_kg = "kg" in unidad or "kilogramo" in unidad

                        codigo = ""
                        for prod in self.productos_config:
                            if prod["nombre"].lower() == nombre or nombre in prod["nombre"].lower():
                                codigo = prod["codigo_arca"]
                                break

                        datos["productos"].append({
                            "nombre": bloque[0].strip(),
                            "codigo_arca": codigo,
                            "cantidad": cantidad,
                            "precio": precio,
                            "es_kg": es_kg
                        })
                    except (ValueError, IndexError):
                        continue
        except Exception:
            datos["cae_original"] = ""

        return datos

    def listar_precios_carpeta(self):
        ruta = self._get_carpeta_seleccionada()
        if not ruta:
            return
        # Buscar el item de la fecha en el tree para agregar hijos
        sel = self.archivo_tree.selection()
        if not sel:
            return
        fecha_id = sel[0]

        # Quitar hijos previos del "Listar Precios" si existen
        for child in self.archivo_tree.get_children(fecha_id):
            if self.archivo_tree.item(child, "text") == "--- Totales ---":
                self.archivo_tree.delete(child)

        pdfs = [self.archivo_tree.item(child, "text") for child in self.archivo_tree.get_children(fecha_id) if self.archivo_tree.item(child, "text").lower().endswith(".pdf")]
        if not pdfs:
            self.log_message("No hay PDFs en la carpeta seleccionada.")
            return

        precios_id = self.archivo_tree.insert(fecha_id, "end", text="          --- Totales ---", open=True)
        self._datos_precios = []
        for pdf in pdfs:
            total = self._extraer_total_pdf(os.path.join(ruta, pdf))
            if total is not None:
                total_str = f"${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                total_str = "N/A"
            nombre_corto = pdf.split("_")[-1].replace(".pdf", "")
            nro = pdf.split("_")[-1].replace(".pdf", "")
            self._datos_precios.append({"nro": nro, "total": total, "total_str": total_str})
            self.archivo_tree.insert(precios_id, "end", text=f"     {nro}  →  {total_str}")

        self.archivo_tree.see(precios_id)
        self._save_pdf_cache()
        self._actualizar_botones()
        self.log_message(f"Precios listados para {len(pdfs)} factura(s).")

    def copiar_nros_comprobante(self):
        if not self._datos_precios:
            return
        texto = "\n".join(d["nro"] for d in self._datos_precios)
        import subprocess
        subprocess.run(["powershell", "-Command", f"'{texto}' | Set-Clipboard"], capture_output=True)
        self.log_message(f"{len(self._datos_precios)} nro(s) de comprobante copiado(s) al portapapeles.")

    def copiar_totales_precios(self):
        if not self._datos_precios:
            return
        lineas = []
        for d in self._datos_precios:
            if d["total"] is not None:
                total_fmt = f"{d['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                lineas.append(total_fmt)
            else:
                lineas.append("N/A")
        texto = "\n".join(lineas)
        import subprocess
        subprocess.run(["powershell", "-Command", f"'{texto}' | Set-Clipboard"], capture_output=True)
        self.log_message(f"{len(self._datos_precios)} total(es) copiado(s) al portapapeles.")

    def eliminar_pdf_seleccionado(self):
        ruta = self._get_pdf_seleccionado()
        if not ruta:
            return
        nombre = os.path.basename(ruta)
        if not messagebox.askyesno("Confirmar eliminación", f"¿Estás seguro de eliminar {nombre}?"):
            return
        try:
            os.remove(ruta)
            self.log_message(f"Eliminado: {nombre}")
            self.refresh_archivo_tree()
        except Exception as e:
            self.log_message(f"Error al eliminar: {str(e)}")

    def generar_reporte_diario(self):
        fecha = getattr(self, "combo_archivo_remito", None)
        fecha_val = fecha.get() if fecha else ""
        if not fecha_val or fecha_val == "- Todos -":
            self.log_message("Error: Seleccioná una Fecha de Remito específica para generar el reporte.")
            return
        fecha = fecha_val

        import re
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        base_path = os.path.join(desktop, "facturas")
        datos_por_cliente = {"Kilbel": [], "Tunel": []}

        for cliente_nombre, carpeta in [("Kilbel", "kilbel"), ("Tunel", "tunel")]:
            ruta_fecha = os.path.join(base_path, carpeta, fecha)
            if not os.path.isdir(ruta_fecha):
                continue
            all_pdfs = [f for f in os.listdir(ruta_fecha) if f.lower().endswith(".pdf")]
            factura_pdfs = [f for f in all_pdfs if f.startswith("Factura_")]
            nc_pdfs = [f for f in all_pdfs if f.startswith("Nota_Credito_")]

            nc_map = {}
            for nc_pdf in nc_pdfs:
                ruta_nc = os.path.join(ruta_fecha, nc_pdf)
                orig_pv, orig_nro = self._extraer_factura_original_desde_nc(ruta_nc)
                if orig_nro:
                    nc_match = re.search(r'_(\d{5})_(\d{8})\.pdf$', nc_pdf)
                    if nc_match:
                        nc_self_nro = f"{nc_match.group(1)}-{nc_match.group(2)}"
                        nc_total = self._extraer_total_pdf(ruta_nc)
                        nc_map[orig_nro] = {"nro": nc_self_nro, "total": nc_total}

            for pdf_name in factura_pdfs:
                ruta_pdf = os.path.join(ruta_fecha, pdf_name)
                match = re.search(r'_(\d{5})_(\d{8})\.pdf$', pdf_name)
                if not match:
                    continue
                nro_comp = f"{match.group(1)}-{match.group(2)}"
                nro_int = int(match.group(2))
                total = self._extraer_total_pdf(ruta_pdf)
                if total is not None:
                    entry = {"nro": nro_comp, "total": total}
                    if nro_int in nc_map:
                        entry["nc"] = nc_map[nro_int]
                    datos_por_cliente[cliente_nombre].append(entry)

        for cliente in datos_por_cliente:
            datos_por_cliente[cliente].sort(key=lambda x: int(x["nro"].split("-")[1]))

        if not any(datos_por_cliente.values()):
            self.log_message(f"No se encontraron facturas para la fecha {fecha}.")
            return

        import pdf_generator
        fecha_archivo = fecha.replace("/", "-")
        output_path = os.path.join(desktop, f"Reporte_Diario_{fecha_archivo}.pdf")
        pdf_generator.generar_reporte_diario(fecha, datos_por_cliente, output_path)

        self.log_message(f"Reporte diario generado: {output_path}")
        if os.name == 'nt':
            os.startfile(output_path)

    def guardar_precios(self):
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        config_path = os.path.join(base_dir, "config.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            nuevos_productos = []
            for p in self.precio_entries:
                prod = p["data"]
                try:
                    nuevo_precio_tunel = float(p["widget_tunel"].get().strip())
                    prod["precio_tunel"] = nuevo_precio_tunel
                    nuevo_precio_kilbel = float(p["widget_kilbel"].get().strip())
                    prod["precio_kilbel"] = nuevo_precio_kilbel
                except ValueError:
                    self.log_message(f"Error: Precio inválido para {prod['nombre']}")
                    return
                nuevos_productos.append(prod)
                
            if isinstance(data, dict):
                data["productos"] = nuevos_productos
            else:
                data = nuevos_productos
                
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            # Actualizar referencias en memoria para la facturación
            for p_fac in self.product_entries:
                for n_prod in nuevos_productos:
                    if p_fac["data"]["codigo_arca"] == n_prod["codigo_arca"]:
                        p_fac["data"]["precio_tunel"] = n_prod["precio_tunel"]
                        p_fac["data"]["precio_kilbel"] = n_prod["precio_kilbel"]
                        
            self.log_message("Precios actualizados y guardados correctamente.")
        else:
            self.log_message("Error: No se encontró config.json")

    def generar_pdf_precios(self):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        import datetime, os

        fecha_hoy = datetime.datetime.now()
        fecha_str = f"{fecha_hoy.day:02d}-{fecha_hoy.month:02d}"
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        
        for cliente, key in [("Tunel", "widget_tunel"), ("Kilbel", "widget_kilbel")]:
            nombre_archivo = f"lista de precios {cliente} ({fecha_str}).pdf"
            ruta_pdf = os.path.join(desktop, nombre_archivo)

            c = canvas.Canvas(ruta_pdf, pagesize=A4)
            width, height = A4
            margin = 30
            y = height - 50

            c.setFont("Helvetica-Bold", 26)
            c.drawCentredString(width / 2, y, "SU BANDEJA")
            y -= 35

            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width / 2, y, f"Lista de Precios - {cliente}")
            y -= 30
            c.setFont("Helvetica", 10)
            c.drawCentredString(width / 2, y, fecha_hoy.strftime("%d/%m/%Y"))
            y -= 40

            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, "Código")
            c.drawString(margin + 100, y, "Producto")
            c.drawString(margin + 350, y, "Precio")
            y -= 20

            c.setFont("Helvetica", 10)
            for p in self.precio_entries:
                codigo = p["data"]["codigo_arca"]
                nombre = p["data"]["nombre"]
                try:
                    precio = float(p[key].get().strip())
                except ValueError:
                    precio = p["data"].get(f"precio_{cliente.lower()}", 0)
                precio_str = f"${precio:.2f}".replace('.', ',')

                c.drawString(margin, y, codigo)
                c.drawString(margin + 100, y, nombre)
                c.drawString(margin + 350, y, precio_str)
                y -= 16

                if codigo == "PRO":
                    y -= 8
                    c.line(margin, y, width - margin, y)
                    y -= 16
                    c.setFont("Helvetica-Bold", 10)
                    c.drawCentredString(width / 2, y, "Precio por Kg")
                    y -= 20
                    c.setFont("Helvetica", 10)

                if y < 50:
                    c.showPage()
                    y = height - 50

            c.save()
            self.log_message(f"PDF de precios generado: {nombre_archivo}")

    def focus_next_widget(self, next_widget):
        next_widget.focus_set()
        
        try:
            is_product = any(p["widget"] == next_widget for p in getattr(self, "product_entries", []))
            if is_product:
                self.update_idletasks()
                
                canvas = self.frame_productos._parent_canvas
                bbox = canvas.bbox("all")
                
                if bbox:
                    total_height = bbox[3] - bbox[1]
                    widget_y = next_widget.winfo_y()
                    
                    # Restamos 35 píxeles para incluir el Label (título del producto) que está encima del entry
                    target_y = max(0, widget_y - 35)
                    fraction = target_y / total_height
                    
                    canvas.yview_moveto(fraction)
            else:
                self.update_idletasks()
                canvas = self.frame_general._parent_canvas
                bbox = canvas.bbox("all")
                if bbox:
                    total_height = bbox[3] - bbox[1]
                    widget_y = next_widget.winfo_y()
                    if widget_y > 250:
                        fraction = (widget_y - 100) / total_height
                        canvas.yview_moveto(fraction)
        except Exception:
            pass
            
        return "break"

    def on_sucursal_type(self, event):
        if event.keysym in ("Return", "Tab"):
            return
        
        cliente = self.combo_cliente.get()
        if cliente == "El Tunel S.A.":
            sucursales = self.sucursales_tunel
        elif cliente == "Kilbel":
            sucursales = self.sucursales_kilbel
        else:
            self.label_sucursal_match.configure(text="")
            self.current_sucursal_matches = []
            return
            
        texto = self.entry_sucursal.get().lower().strip()
        if not texto:
            self.label_sucursal_match.configure(text="")
            self.current_sucursal_matches = []
            return
            
        if cliente == "Kilbel" and texto == "pue":
            matches = ["Remolcador Meteoro 2760 Piso:DIQII Dpto:25 - Santa Fe, Santa Fe"]
        elif cliente == "Kilbel" and texto == "la":
            matches = ["San Jose 2629 - Santa Fe, Santa Fe"]
        elif cliente == "El Tunel S.A." and texto in ("cen", "cent"):
            matches = ["Av Fray Cayetano Rodriguez 3845 - Santa Fe, Santa Fe"]
        elif cliente == "El Tunel S.A." and texto in ("sui", "su", "suip"):
            matches = ["Saavedra 3101 - Santa Fe, Santa Fe"]
        elif cliente == "El Tunel S.A." and texto in ("pe", "peñ", "pen"):
            matches = ["Estanislao Zeballos 3998 - Santa Fe, Santa Fe"]
        elif cliente == "El Tunel S.A." and texto in ("aris", "ar", "ari"):
            matches = ["Avenida Aristobulo Del Valle 7934 - Santa Fe, Santa Fe"]
        else:
            palabras = texto.split()
            matches = [s for s in sucursales if all(p in s.lower() for p in palabras)]
            
        self.current_sucursal_matches = matches
        
        if len(matches) == 1:
            self.label_sucursal_match.configure(text=matches[0], text_color="green")
        elif len(matches) > 1:
            self.label_sucursal_match.configure(text=f"{len(matches)} coincidencias...", text_color="gray")
        else:
            self.label_sucursal_match.configure(text="Sin coincidencias", text_color="red")

    def handle_sucursal_enter(self, event, next_widget):
        if hasattr(self, 'current_sucursal_matches') and len(self.current_sucursal_matches) > 0:
            self.entry_sucursal.delete(0, "end")
            self.entry_sucursal.insert(0, self.current_sucursal_matches[0])
            self.label_sucursal_match.configure(text="")
            self.focus_next_widget(next_widget)
        else:
            self.log_message("Debés seleccionar una sucursal válida de las sugeridas.")
        return "break"

    def handle_cliente_enter(self, event):
        val = self.combo_cliente.get().strip()
        if val == "k" or val == "K":
            self.combo_cliente.set("Kilbel")
            val = "Kilbel"
        elif val == "t" or val == "T":
            self.combo_cliente.set("El Tunel S.A.")
            val = "El Tunel S.A."
            
        if val in ("Kilbel", "El Tunel S.A."):
            self.focus_next_widget(self.entry_sucursal)
        else:
            self.log_message("Debés seleccionar 'Kilbel' o 'El Tunel S.A.' como cliente.")
        return "break"
    def handle_product_enter(self, event, current_widget, next_widget):
        val = current_widget.get().strip()
        if val == "":
            current_widget.insert(0, "0")
        
        self.focus_next_widget(next_widget)
        return "break"
    
    def handle_product_shift_enter(self, event, prev_widget):
        self.focus_next_widget(prev_widget)
        return "break"

    def format_fecha(self, event):
        if event.keysym in ("Return", "Tab", "BackSpace", "Delete", "Left", "Right", "Home", "End"):
            return
        texto = self.entry_fecha.get()
        solo_digitos = "".join(c for c in texto if c.isdigit())[:8]
        formateado = ""
        for i, c in enumerate(solo_digitos):
            if i in (2, 4):
                formateado += "/"
            formateado += c
        self.entry_fecha.delete(0, "end")
        self.entry_fecha.insert(0, formateado)

    def _validate_only_digits(self, proposed, max_len):
        if proposed == "":
            return True
        if not proposed.isdigit():
            return False
        if len(proposed) > int(max_len):
            return False
        return True

    def _validate_remito(self, proposed):
        if not proposed.isdigit():
            return False
        if len(proposed) > 8:
            return False
        if len(proposed) >= 4 and proposed[:4] != "0000":
            return False
        if len(proposed) < 4:
            return False
        return True

    def _validate_no_digits(self, proposed):
        if proposed == "":
            return True
        return not any(c.isdigit() for c in proposed)

    def _validate_product_qty(self, proposed):
        if proposed == "":
            return True
        return all(c.isdigit() or c == ',' for c in proposed)

    def handle_remito_enter(self, event):
        val = self.entry_remito.get().strip()
        if len(val) != 8:
            self.log_message(f"El remito debe tener 8 dígitos (actual: {len(val)})")
            return "break"
        self.focus_next_widget(self.combo_cliente)
        return "break"

    def handle_remito_focus_out(self, event):
        self.entry_remito.configure(border_color="#565656")
        if getattr(self, '_limpiando', False):
            return
        val = self.entry_remito.get().strip()
        if len(val) > 0 and len(val) < 8:
            self.entry_remito.focus_set()

    def log_message(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", f"{message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def _get_next_comprobante_nro(self):
        import re
        folder_name = "facturas_prueba" if self.modo_prueba.get() else "facturas"
        base_path = os.path.join(os.path.expanduser("~"), "Desktop", folder_name)
        max_nro = 0
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        match = re.search(r'_(\d{8})\.pdf$', f)
                        if match:
                            nro = int(match.group(1))
                            if nro > max_nro:
                                max_nro = nro
        return max_nro + 1

    def run_simulacion(self, datos, open_pdf=True):
        import datetime
        siguiente_nro = self._get_next_comprobante_nro()
        punto_venta = 3
        cae = f"6423456789{siguiente_nro:04d}"
        vto_cae = "20261231"

        datos["fecha_emision"] = datetime.datetime.now().strftime("%d/%m/%Y")

        self.log_message(f"[SIMULACION] Comprobante: {punto_venta:05d}-{siguiente_nro:08d}")
        self.log_message(f"[SIMULACION] CAE: {cae}")

        try:
            import pdf_generator
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            cliente_nombre = datos.get("cliente_nombre", "")
            cliente_folder = "kilbel" if cliente_nombre == "Kilbel" else "tunel"

            if not datos.get("fecha"):
                datos["fecha"] = datetime.datetime.now().strftime("%d/%m/%Y")
            fecha_remito_str = datos["fecha"].replace("/", "-")
            fecha_facturacion_str = datetime.datetime.now().strftime("%d-%m-%Y")
            fecha_carpeta = fecha_remito_str

            facturas_dir = os.path.join(desktop_dir, "facturas_prueba", cliente_folder, fecha_carpeta)
            os.makedirs(facturas_dir, exist_ok=True)

            pdf_filename = f"Factura_A_{punto_venta:05d}_{siguiente_nro:08d}.pdf"
            pdf_path = os.path.join(facturas_dir, pdf_filename)
            pdf_generator.generar_pdf_factura(datos, cae, vto_cae, siguiente_nro, pdf_path, punto_venta)

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
                import base_datos
                fecha_bd = datetime.datetime.strptime(datos["fecha"], "%d/%m/%Y").strftime("%Y-%m-%d")
                sucursal = datos.get("sucursal", "Desconocida")
                
                # Calcular el total para la simulación
                neto = sum([p['cantidad'] * p['precio'] for p in datos['productos']])
                bonificacion = 0.11 if cliente_nombre == "Kilbel" else 0.0
                neto = neto - (neto * bonificacion)
                neto = round(neto, 2)
                iva_calc = round(neto * 0.105, 2)
                total_factura = round(neto + iva_calc, 2)
                
                # base_datos.registrar_venta(fecha_bd, sucursal, total_factura)
                self.log_message(f"[SIMULACION] Venta omitida en base de datos.")
            except Exception as e_bd:
                self.log_message(f"[SIMULACION] Error al registrar venta: {str(e_bd)}")

            self.log_message(f"[SIMULACION] PDF generado: {pdf_filename}")

            if open_pdf and os.name == 'nt':
                os.startfile(pdf_path)

            return True
        except Exception as e:
            self.log_message(f"[SIMULACION] Error al generar PDF: {str(e)}")
            return False

    def generar_preview_pdf(self, datos):
        import datetime
        siguiente_nro = self._get_next_comprobante_nro()
        punto_venta = 3
        cae = f"6423456789{siguiente_nro:04d}"
        vto_cae = "20261231"
        datos["fecha_emision"] = datetime.datetime.now().strftime("%d/%m/%Y")

        import pdf_generator
        temp_dir = tempfile.mkdtemp()
        pdf_filename = f"Factura_A_{punto_venta:05d}_{siguiente_nro:08d}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)
        pdf_generator.generar_pdf_factura(datos, cae, vto_cae, siguiente_nro, pdf_path, punto_venta)

        self.log_message(f"Vista previa generada: {pdf_filename}")
        return pdf_path, siguiente_nro, punto_venta, cae, vto_cae

    def show_preview_popup(self, pdf_path, datos, nro, pv, cae, vto):
        popup = ctk.CTkToplevel(self)
        popup.title(f"Vista Previa - Factura A {pv:05d}-{nro:08d}")
        popup.geometry("850x700")
        popup.transient(self)
        popup.grab_set()
        popup.lift()

        popup._temp_dir = os.path.dirname(pdf_path)

        header_text = f"Factura A {pv:05d}-{nro:08d} | CAE: {cae} | {datos['cliente_nombre']}"
        ctk.CTkLabel(popup, text=header_text, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))

        frame_scroll = ctk.CTkScrollableFrame(popup)
        frame_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        import fitz
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            zoom = 750 / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img_data = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ctk_img = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(pix.width, pix.height))
            label = ctk.CTkLabel(frame_scroll, image=ctk_img, text="")
            label.pack(pady=5)
            label._img_ref = ctk_img
        doc.close()

        frame_btn = ctk.CTkFrame(popup)
        frame_btn.pack(fill="x", padx=10, pady=10)

        btn_generar = ctk.CTkButton(
            frame_btn, text="Generar Factura", height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=lambda: self.finalizar_desde_preview(popup, datos)
        )
        btn_generar.pack(side="right", padx=5)

        btn_cancelar = ctk.CTkButton(
            frame_btn, text="Cancelar", height=40,
            command=lambda: self._cerrar_preview(popup),
            fg_color="gray"
        )
        btn_cancelar.pack(side="right", padx=5)

        popup.protocol("WM_DELETE_WINDOW", lambda: self._cerrar_preview(popup))
        popup.bind("<Return>", lambda e: self.finalizar_desde_preview(popup, datos))
        popup.after(50, lambda: btn_generar.focus_set())

    def _cerrar_preview(self, popup):
        temp_dir = getattr(popup, '_temp_dir', None)
        popup.destroy()
        self._preview_open = False
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    def finalizar_desde_preview(self, popup, datos):
        temp_dir = getattr(popup, '_temp_dir', None)
        popup.destroy()
        self._preview_open = False
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        self._generating = True
        self.btn_generar.configure(state="disabled")
        self.log_message("--- Generando factura final ---")
        t = threading.Thread(target=self.run_finalizar_thread, args=(datos,))
        t.daemon = True
        t.start()

    def get_data(self):
        cliente_seleccionado = self.combo_cliente.get()
        cuit_map = {
            "El Tunel S.A.": "30518084557",
            "Kilbel": "30681989567"
        }
        
        datos = {
            "fecha": self.entry_fecha.get().strip(),
            "orden": self.entry_orden.get().strip(),
            "remito": self.entry_remito.get().strip(),
            "cliente_nombre": cliente_seleccionado,
            "cuit_cliente": cuit_map.get(cliente_seleccionado, ""),
            "sucursal": self.entry_sucursal.get().strip(),
            "productos": []
        }
        
        provenzal_idx = next((i for i, p in enumerate(self.product_entries) if p["data"]["codigo_arca"] == "PRO"), -1)

        for idx, p in enumerate(self.product_entries):
            val = p["widget"].get().strip()
            # Si está vacío o es 0, lo ignoramos para la factura real
            if val == "": val = "0"
            try:
                es_kg = idx > provenzal_idx
                if es_kg:
                    cantidad = float(val.replace(",", "."))
                else:
                    cantidad = int(val)
                if cantidad > 0:
                    if cliente_seleccionado == "El Tunel S.A.":
                        precio = p["data"].get("precio_tunel", p["data"].get("precio", 0))
                    elif cliente_seleccionado == "Kilbel":
                        precio = p["data"].get("precio_kilbel", p["data"].get("precio", 0))
                    else:
                        precio = p["data"].get("precio", 0)

                    datos["productos"].append({
                        "nombre": p["data"]["nombre"],
                        "codigo_arca": p["data"]["codigo_arca"],
                        "precio": precio,
                        "cantidad": cantidad,
                        "es_kg": es_kg
                    })
            except ValueError:
                self.log_message(f"Valor inválido en cantidad de {p['data']['nombre']}: {val}")
        
        return datos

    def on_generar_click(self):
        if getattr(self, '_generating', False) or getattr(self, '_preview_open', False):
            return
        self._preview_open = True
        datos = self.get_data()
        
        if not datos["fecha"]:
            self.log_message("Error: La fecha del remito es obligatoria.")
            self._preview_open = False
            self.entry_fecha.focus_set()
            return
            
        if len(datos["remito"]) != 8:
            self.log_message("Error: El número de remito debe tener 8 dígitos.")
            self._preview_open = False
            self.entry_remito.focus_set()
            return
            
        if not datos["cuit_cliente"] or len(datos["cuit_cliente"]) != 11:
            self.log_message("Error: El CUIT del cliente debe tener 11 dígitos.")
            self._preview_open = False
            return
            
        if not datos["productos"]:
            self.log_message("Error: Debes cargar al menos un producto mayor a 0.")
            self._preview_open = False
            return
            
        self.log_message("--- Generando vista previa ---")
        if self.modo_prueba.get():
            self.log_message("⚠ MODO PRUEBA - Vista previa simulada")
        
        try:
            pdf_path, nro, pv, cae, vto = self.generar_preview_pdf(datos)
            self.show_preview_popup(pdf_path, datos, nro, pv, cae, vto)
        except Exception as e:
            self.log_message(f"Error al generar vista previa: {str(e)}")
            self._preview_open = False
    
    def run_finalizar_thread(self, datos):
        if self.modo_prueba.get():
            resultado = self.run_simulacion(datos, open_pdf=False)
        else:
            resultado = self.start_bot_callback(datos, self.log_message)
        if resultado:
            self.log_message("Proceso finalizado correctamente.")
            self.after(0, self.limpiar_campos)
        else:
            self.log_message("Proceso finalizado con errores.")
        self.after(0, lambda: self.btn_generar.configure(state="normal"))
        self.after(0, lambda: setattr(self, '_generating', False))
        
    def limpiar_campos(self):
        self._limpiando = True
        # Autoincrementar remito
        remito_actual = self.entry_remito.get().strip()
        if remito_actual.isdigit():
            siguiente = str(int(remito_actual) + 1).zfill(len(remito_actual))
            self.entry_remito.configure(validate='none')
            self.entry_remito.delete(0, 'end')
            self.entry_remito.insert(0, siguiente)
            self.entry_remito.configure(validate='key', validatecommand=(self.register(self._validate_remito), '%P'))
            self.log_message(f"Remito auto-incrementado: {remito_actual} → {siguiente}")
        else:
            self.entry_remito.delete(0, 'end')
            
        self.combo_cliente.set("")
        self.entry_sucursal.delete(0, 'end')
        if hasattr(self, 'label_sucursal_match'):
            self.label_sucursal_match.configure(text="")
        for p in self.product_entries:
            p["widget"].delete(0, 'end')
            
        self.combo_cliente.focus_set()
        if hasattr(self.combo_cliente, "_entry"):
            self.combo_cliente._entry.focus_set()
            
        self._limpiando = False
        self.log_message("Campos preparados para el siguiente remito.")

    def on_generar_nota_credito(self):
        if getattr(self, '_generating', False):
            return
        ruta_pdf = self._get_pdf_seleccionado()
        if not ruta_pdf:
            self.log_message("Error: Seleccioná una factura PDF para generar la nota de crédito.")
            return

        self._generating = True
        self.btn_nota_credito.configure(state="disabled")

        datos_original = self._extraer_datos_desde_pdf(ruta_pdf)

        if not datos_original.get("cuit_cliente"):
            self.log_message("Error: No se pudo determinar el cliente de la factura seleccionada.")
            self._generating = False
            self.btn_nota_credito.configure(state="normal")
            return

        if not datos_original.get("imp_total"):
            self.log_message("Error: No se pudo leer el importe total de la factura seleccionada.")
            self._generating = False
            self.btn_nota_credito.configure(state="normal")
            return

        self.log_message("--- Generando Nota de Crédito ---")
        self.log_message(f"Factura original: {datos_original.get('punto_venta_original', 0):05d}-{datos_original.get('nro_comprobante_original', 0):08d}")
        self.log_message(f"Cliente: {datos_original.get('cliente_nombre')} | Total: ${datos_original.get('imp_total', 0):.2f}")
        if self.modo_prueba.get():
            self.log_message("⚠ MODO PRUEBA ACTIVADO - No se generarán comprobantes reales en ARCA")

        t = threading.Thread(target=self._run_nota_credito_thread, args=(datos_original,))
        t.daemon = True
        t.start()

    def _run_nota_credito_thread(self, datos_original):
        if self.modo_prueba.get():
            resultado = self._run_nota_credito_simulacion(datos_original)
        elif self.start_nota_credito_callback:
            resultado = self.start_nota_credito_callback(datos_original, self.log_message)
        else:
            self.log_message("Error: No hay callback configurado para notas de crédito.")
            resultado = False

        if resultado:
            self.log_message("Nota de crédito generada correctamente.")
        else:
            self.log_message("Error al generar la nota de crédito.")

        self.after(0, lambda: self.btn_nota_credito.configure(state="normal"))
        self.after(0, lambda: setattr(self, '_generating', False))

    def _run_nota_credito_simulacion(self, datos_original, open_pdf=True):
        import datetime
        siguiente_nro = self._get_next_nota_credito_nro()
        punto_venta = 3
        cae = f"6423456789{siguiente_nro:04d}"
        vto_cae = "20261231"

        datos_original["fecha_emision"] = datetime.datetime.now().strftime("%d/%m/%Y")

        self.log_message(f"[SIMULACION] Nota de Crédito: {punto_venta:05d}-{siguiente_nro:08d}")
        self.log_message(f"[SIMULACION] CAE: {cae}")

        try:
            import pdf_generator
            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            cliente_nombre = datos_original.get("cliente_nombre", "")
            cliente_folder = "kilbel" if cliente_nombre == "Kilbel" else "tunel"

            if not datos_original.get("fecha"):
                datos_original["fecha"] = datetime.datetime.now().strftime("%d/%m/%Y")
            fecha_remito_str = datos_original["fecha"].replace("/", "-")
            fecha_carpeta = datetime.datetime.now().strftime("%d-%m-%Y")

            facturas_dir = os.path.join(desktop_dir, "facturas_prueba", cliente_folder, fecha_carpeta)
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
            metadatos[pdf_filename] = fecha_remito_str
            try:
                with open(metadatos_path, "w", encoding="utf-8") as f:
                    json.dump(metadatos, f, indent=4)
            except Exception:
                pass

            self.log_message(f"[SIMULACION] PDF generado: {pdf_filename}")
            if open_pdf and os.name == 'nt':
                os.startfile(pdf_path)

            return True
        except Exception as e:
            self.log_message(f"[SIMULACION] Error al generar PDF: {str(e)}")
            return False

    def _get_next_nota_credito_nro(self):
        import re
        folder_name = "facturas_prueba" if self.modo_prueba.get() else "facturas"
        base_path = os.path.join(os.path.expanduser("~"), "Desktop", folder_name)
        max_nro = 0
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f.startswith("Nota_Credito_A") and f.lower().endswith(".pdf"):
                        match = re.search(r'_(\d{8})\.pdf$', f)
                        if match:
                            nro = int(match.group(1))
                            if nro > max_nro:
                                max_nro = nro
        return max_nro + 1

    def _is_newer(self, latest, current):
        try:
            l_parts = [int(x) for x in latest.split(".")]
            c_parts = [int(x) for x in current.split(".")]
            return l_parts > c_parts
        except:
            return False

    def check_for_updates(self):
        import json
        try:
            url = "https://api.github.com/repos/nachofigue/sistema-facturacion/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                
            latest_version = data.get("tag_name", "").lstrip("v")
            current_version = APP_VERSION
            
            if self._is_newer(latest_version, current_version):
                assets = data.get("assets", [])
                download_url = None
                for asset in assets:
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                
                if download_url:
                    self.after(2000, lambda: self.show_update_popup(latest_version, download_url))
        except Exception as e:
            pass # Falla silenciosamente si no hay internet o el repo es privado

    def show_update_popup(self, version, download_url):
        popup = ctk.CTkToplevel(self)
        popup.title("¡Actualización Disponible!")
        popup.geometry("400x200")
        popup.transient(self)
        popup.grab_set()
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - popup.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(popup, text=f"Hay una nueva versión disponible ({version}).", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        ctk.CTkLabel(popup, text="¿Deseas descargarla e instalarla ahora?", font=ctk.CTkFont(size=14)).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_accept():
            popup.destroy()
            self.perform_update(download_url)
            
        def on_cancel():
            popup.destroy()
            
        ctk.CTkButton(btn_frame, text="Sí, actualizar", command=on_accept, fg_color="#2e7d32", hover_color="#1b5e20").pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Más tarde", command=on_cancel, fg_color="#c0392b", hover_color="#922b21").pack(side="right", padx=10)

    def perform_update(self, download_url):
        self.log_message("Descargando actualización... Por favor, espere (la pantalla puede congelarse unos segundos).")
        
        def download_and_install():
            import sys
            import subprocess
            try:
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    self.after(0, lambda: self.log_message("No se puede actualizar automáticamente en modo script (.py)."))
                    return
                
                update_exe_path = exe_path + ".new"
                
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(update_exe_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                bat_path = os.path.join(os.path.dirname(exe_path), "update.bat")
                bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
del "{exe_path}"
ren "{update_exe_path}" "{os.path.basename(exe_path)}"
start "" "{exe_path}"
del "%~f0"
"""
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)
                
                self.after(0, lambda: self.log_message("Descarga completada. Reiniciando para aplicar actualización..."))
                subprocess.Popen([bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
                
                self.after(1000, self.quit)
                
            except Exception as e:
                self.after(0, lambda: self.log_message(f"Error al actualizar: {e}"))
                
        threading.Thread(target=download_and_install, daemon=True).start()
