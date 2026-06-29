import customtkinter as ctk
import json
import os
import threading

class FacturaApp(ctk.CTk):
    def __init__(self, start_bot_callback):
        super().__init__()
        
        self.start_bot_callback = start_bot_callback
        
        # Configuración de ventana
        self.title("Automatización de Facturas - ARCA")
        self.geometry("900x700")
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
        
        self.setup_ui()
        
    def load_config(self):
        import sys
        # Si se ejecuta como .exe, toma la ruta del ejecutable o entorno temporal, sino la del script.
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
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
        
        self.tab_facturacion.grid_columnconfigure(0, weight=1)
        self.tab_facturacion.grid_columnconfigure(1, weight=1)
        self.tab_facturacion.grid_rowconfigure(0, weight=1)
        
        # --- SECCIÓN A: Datos Generales (Columna 0) ---
        self.frame_general = ctk.CTkScrollableFrame(self.tab_facturacion)
        self.frame_general.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.frame_general, text="Datos del Remito", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Fecha del Remito
        ctk.CTkLabel(self.frame_general, text="Fecha del Remito (DD/MM/AAAA)").pack(anchor="w", padx=20)
        self.entry_fecha = ctk.CTkEntry(self.frame_general, placeholder_text="DD/MM/AAAA")
        self.entry_fecha.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_fecha.bind("<Return>", lambda e: self.focus_next_widget(self.entry_orden))

        # Número de Orden
        ctk.CTkLabel(self.frame_general, text="Número de Orden").pack(anchor="w", padx=20)
        self.entry_orden = ctk.CTkEntry(self.frame_general, placeholder_text="0001")
        self.entry_orden.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_orden.bind("<Return>", lambda e: self.focus_next_widget(self.entry_remito))
        
        # Número de Remito
        ctk.CTkLabel(self.frame_general, text="Número de Remito").pack(anchor="w", padx=20)
        self.entry_remito = ctk.CTkEntry(self.frame_general)
        self.entry_remito.pack(fill="x", padx=20, pady=(0, 15))
        self.entry_remito.bind("<Return>", lambda e: self.focus_next_widget(self.combo_cliente))
        
        # Cliente (Dropdown)
        ctk.CTkLabel(self.frame_general, text="Cliente").pack(anchor="w", padx=20)
        self.combo_cliente = ctk.CTkComboBox(self.frame_general, values=["El Tunel S.A.", "Kilbel"])
        self.combo_cliente.pack(fill="x", padx=20, pady=(0, 15))
        # Bindear Enter en el combobox para autocompletar 'k' y 't'
        if hasattr(self.combo_cliente, "_entry"):
            self.combo_cliente._entry.bind("<Return>", self.handle_cliente_enter)
        else:
            self.combo_cliente.bind("<Return>", self.handle_cliente_enter)
        
        
        # Sucursal
        ctk.CTkLabel(self.frame_general, text="Sucursal del Supermercado").pack(anchor="w", padx=20)
        self.entry_sucursal = ctk.CTkEntry(self.frame_general)
        self.entry_sucursal.pack(fill="x", padx=20, pady=(0, 5))
        
        self.label_sucursal_match = ctk.CTkLabel(self.frame_general, text="", text_color="gray", font=ctk.CTkFont(size=12))
        self.label_sucursal_match.pack(anchor="w", padx=20, pady=(0, 15))
        self.entry_sucursal.bind("<KeyRelease>", self.on_sucursal_type)
        
        self.entry_remito.insert(0, "") 
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
                entry = ctk.CTkEntry(self.frame_productos, placeholder_text="0")
                if index == 0:
                    entry.insert(0, "1") # DATO DE PRUEBA
                entry.pack(fill="x", padx=10, pady=(0, 5))
                self.product_entries.append({
                    "data": prod,
                    "widget": entry
                })
            
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
        else:
            ctk.CTkLabel(self.frame_productos, text="No se encontraron productos en config.json").pack(pady=20)
            self.entry_sucursal.bind("<Return>", lambda e: self.handle_sucursal_enter(e, self.btn_generar))

        # Botón Generar
        self.btn_generar = ctk.CTkButton(self.frame_general, text="Generar Factura en ARCA", height=40, font=ctk.CTkFont(size=15, weight="bold"), command=self.on_generar_click)
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
        
        self.console_visible = True
        self.btn_toggle_console = ctk.CTkButton(self, text="Ocultar Consola", width=120, height=28, command=self.toggle_console)
        self.btn_toggle_console.place(relx=0.98, y=15, anchor="ne")
        
        # Foco inicial
        self.entry_fecha.focus_set()

    def toggle_console(self):
        if self.console_visible:
            self.frame_logs.grid_remove()
            self.btn_toggle_console.configure(text="Mostrar Consola")
            self.console_visible = False
        else:
            self.frame_logs.grid()
            self.btn_toggle_console.configure(text="Ocultar Consola")
            self.console_visible = True

    def setup_precios_tab(self):
        self.tab_precios.grid_columnconfigure(0, weight=1)
        self.tab_precios.grid_rowconfigure(0, weight=1)
        
        self.frame_precios = ctk.CTkScrollableFrame(self.tab_precios)
        self.frame_precios.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.precio_entries = []
        if self.productos_config:
            for index, prod in enumerate(self.productos_config):
                row_frame = ctk.CTkFrame(self.frame_precios)
                row_frame.pack(fill="x", padx=10, pady=5)
                
                ctk.CTkLabel(row_frame, text=prod["nombre"].upper(), width=300, anchor="w").pack(side="left", padx=10)
                
                entry = ctk.CTkEntry(row_frame, width=150)
                entry.insert(0, str(prod["precio"]))
                entry.pack(side="right", padx=10)
                
                self.precio_entries.append({"data": prod, "widget": entry})
                
        self.btn_guardar_precios = ctk.CTkButton(self.tab_precios, text="Guardar Cambios", command=self.guardar_precios)
        self.btn_guardar_precios.grid(row=1, column=0, pady=10)

    def guardar_precios(self):
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
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
                    nuevo_precio = float(p["widget"].get().strip())
                    prod["precio"] = nuevo_precio
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
                        p_fac["data"]["precio"] = n_prod["precio"]
                        
            self.log_message("Precios actualizados y guardados correctamente.")
        else:
            self.log_message("Error: No se encontró config.json")

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
        return "break"

    def handle_cliente_enter(self, event):
        val = self.combo_cliente.get().strip().lower()
        if val == "k":
            self.combo_cliente.set("Kilbel")
        elif val == "t":
            self.combo_cliente.set("El Tunel S.A.")
            
        self.focus_next_widget(self.entry_sucursal)
        return "break"
    def handle_product_enter(self, event, current_widget, next_widget):
        val = current_widget.get().strip()
        if val == "":
            current_widget.insert(0, "0")
        
        self.focus_next_widget(next_widget)
        return "break"

    def log_message(self, message):
        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", f"{message}\n")
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

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
        
        for p in self.product_entries:
            val = p["widget"].get().strip()
            # Si está vacío o es 0, lo ignoramos para la factura real
            if val == "": val = "0"
            try:
                cantidad = int(val)
                if cantidad > 0:
                    datos["productos"].append({
                        "nombre": p["data"]["nombre"],
                        "codigo_arca": p["data"]["codigo_arca"],
                        "precio": p["data"]["precio"],
                        "cantidad": cantidad
                    })
            except ValueError:
                self.log_message(f"Valor inválido en cantidad de {p['data']['nombre']}: {val}")
        
        return datos

    def on_generar_click(self):
        # Deshabilitar botón para evitar dobles clicks
        self.btn_generar.configure(state="disabled")
        datos = self.get_data()
        
        if not datos["fecha"]:
            self.log_message("Error: La fecha del remito es obligatoria.")
            self.btn_generar.configure(state="normal")
            self.entry_fecha.focus_set()
            return
            
        if not datos["remito"]:
            self.log_message("Error: El número de remito es obligatorio.")
            self.btn_generar.configure(state="normal")
            self.entry_remito.focus_set()
            return
            
        if not datos["cuit_cliente"] or len(datos["cuit_cliente"]) != 11:
            self.log_message("Error: El CUIT del cliente debe tener 11 dígitos.")
            self.btn_generar.configure(state="normal")
            return
            
        if not datos["productos"]:
            self.log_message("Error: Debes cargar al menos un producto mayor a 0.")
            self.btn_generar.configure(state="normal")
            return
            
        self.log_message("--- Iniciando proceso de facturación ---")
        self.log_message(f"Remito: {datos['remito']} | Cliente: {datos['cuit_cliente']} | Sucursal: {datos['sucursal']}")
        self.log_message(f"Productos a facturar: {len(datos['productos'])}")
        
        # Ejecutar en un hilo separado para no bloquear la UI
        t = threading.Thread(target=self.run_bot_thread, args=(datos,))
        t.daemon = True
        t.start()
        
    def run_bot_thread(self, datos):
        resultado = self.start_bot_callback(datos, self.log_message)
        if resultado:
            self.log_message("Proceso finalizado correctamente.")
            # Solo avanzar campos si fue exitoso
            self.after(0, self.limpiar_campos)
        else:
            self.log_message("Proceso finalizado con errores.")
        
        # Rehabilitar botón en el hilo principal
        self.after(0, lambda: self.btn_generar.configure(state="normal"))
        
    def limpiar_campos(self):
        # Autoincrementar remito
        remito_actual = self.entry_remito.get().strip()
        if remito_actual.isdigit():
            siguiente = str(int(remito_actual) + 1).zfill(len(remito_actual))
            self.entry_remito.delete(0, 'end')
            self.entry_remito.insert(0, siguiente)
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
            
        self.log_message("Campos preparados para el siguiente remito.")
