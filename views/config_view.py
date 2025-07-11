# views/config_view.py

import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os

CONFIG_PATH = "config/config.json"

class ConfigView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ECECEC")

        self.campos = {
            "csv_chats": tk.StringVar(),
            "csv_intents": tk.StringVar(),
            "output_folder": tk.StringVar(),
            "llm_url": tk.StringVar(),
            "llm_id": tk.StringVar(),
        }

        tk.Label(self, text="⚙️ Configuración", font=("Segoe UI", 18), bg="#ECECEC").pack(pady=20)

        self.contenedor = tk.Frame(self, bg="#ECECEC")
        self.contenedor.pack(pady=10)

        self.crear_entrada("Seleccionar CSV de datos Chats:", "csv_chats", tipo="archivo")
        self.crear_entrada("Seleccionar CSV de datos Intents:", "csv_intents", tipo="archivo")
        self.crear_entrada("Carpeta donde guardar reporte generado:", "output_folder", tipo="directorio")
        self.crear_entrada("URL del LLM:", "llm_url")
        self.crear_entrada("ID del modelo LLM:", "llm_id")

        tk.Button(self, text="Guardar configuración", font=("Segoe UI", 12), bg="#4CAF50", fg="white",
                  command=self.guardar_config).pack(pady=15)

        self.cargar_config()

    def crear_entrada(self, texto, clave, tipo="texto"):
        frame = tk.Frame(self.contenedor, bg="#ECECEC")
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(frame, text=texto, font=("Segoe UI", 10), bg="#ECECEC").pack(side="left")
        entry = tk.Entry(frame, textvariable=self.campos[clave], width=50)
        entry.pack(side="left", padx=10)

        if tipo == "archivo":
            tk.Button(frame, text="📂", command=lambda: self.seleccionar_archivo(clave)).pack(side="left")
        elif tipo == "directorio":
            tk.Button(frame, text="📁", command=lambda: self.seleccionar_directorio(clave)).pack(side="left")

    def seleccionar_archivo(self, clave):
        ruta = filedialog.askopenfilename(title="Seleccionar archivo CSV", filetypes=[("CSV files", "*.csv")])
        if ruta:
            self.campos[clave].set(ruta)

    def seleccionar_directorio(self, clave):
        ruta = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if ruta:
            self.campos[clave].set(ruta)

    def guardar_config(self):
        data = {k: v.get() if not isinstance(v, tk.BooleanVar) else v.get() for k, v in self.campos.items()}
        if any(v == "" for k, v in data.items() if k != "borrar_debug"):
            messagebox.showerror("Error", "Todos los campos deben estar completos.")
            return

        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    def cargar_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    if k in self.campos:
                        self.campos[k].set(v)
