# views/config_view.py
# Configuración del pipeline (local). Al guardar se hace merge con el JSON existente.

import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os

from core.config_loader import get_config_path

# Valores por defecto para pipeline nuevo (se usan si la clave no existe al cargar)
DEFAULTS = {
    "model_path": "",
    "n_ctx": 4096,
    "n_threads": 8,
    "max_workers": 4,
    "write_debug": False,
}

class ConfigView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ECECEC")

        self.campos = {
            "csv_chats": tk.StringVar(),
            "csv_intents": tk.StringVar(),
            "output_folder": tk.StringVar(),
            "model_path": tk.StringVar(),
            "n_ctx": tk.StringVar(),
            "n_threads": tk.StringVar(),
            "max_workers": tk.StringVar(),
        }
        self.campos_bool = {
            "write_debug": tk.BooleanVar(),
        }

        tk.Label(self, text="⚙️ Configuración", font=("Segoe UI", 18), bg="#ECECEC").pack(pady=20)

        self.contenedor = tk.Frame(self, bg="#ECECEC")
        self.contenedor.pack(pady=10)

        self.crear_entrada("CSV de Chats:", "csv_chats", tipo="archivo")
        self.crear_entrada("CSV de Intents/Training:", "csv_intents", tipo="archivo")
        self.crear_entrada("Carpeta de salida (reportes):", "output_folder", tipo="directorio")
        self.crear_entrada("Modelo GGUF (ej. archivo.gguf):", "model_path")
        self.crear_entrada("n_ctx (contexto LLM):", "n_ctx")
        self.crear_entrada("n_threads:", "n_threads")
        self.crear_entrada("max_workers (paralelismo):", "max_workers")
        frame_cb = tk.Frame(self.contenedor, bg="#ECECEC")
        frame_cb.pack(fill="x", padx=20, pady=5)
        tk.Checkbutton(frame_cb, text="write_debug (cases_debug/)", variable=self.campos_bool["write_debug"],
                      bg="#ECECEC").pack(side="left")

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

    def _get_config_path(self):
        return get_config_path()

    def guardar_config(self):
        data_edit = {k: v.get() for k, v in self.campos.items()}
        for k, v in self.campos_bool.items():
            data_edit[k] = v.get()
        if any(data_edit[k] == "" for k in ("csv_chats", "csv_intents", "output_folder")):
            messagebox.showerror("Error", "Completa al menos: CSV Chats, CSV Intents, Carpeta de salida.")
            return
        try:
            n_ctx = int(data_edit.get("n_ctx") or "4096")
            n_threads = int(data_edit.get("n_threads") or "8")
            max_workers = int(data_edit.get("max_workers") or "4")
        except ValueError:
            messagebox.showerror("Error", "n_ctx, n_threads y max_workers deben ser números.")
            return

        config_path = self._get_config_path()
        try:
            existing = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            for k in ("llm_url", "llm_id"):
                existing.pop(k, None)
            # Merge: actualizar solo las claves editables, conservar el resto
            for k, v in data_edit.items():
                if k in ("n_ctx", "n_threads", "max_workers"):
                    existing[k] = int(v) if str(v).strip() else DEFAULTS.get(k, 0)
                else:
                    existing[k] = v
            for k, v in self.campos_bool.items():
                existing[k] = v.get()
            # Asegurar defaults para claves que podrían faltar
            for k, default in DEFAULTS.items():
                if k not in existing:
                    existing[k] = default
            os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    def cargar_config(self):
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self.campos:
                    if v is None:
                        self.campos[k].set("")
                    elif k in ("n_ctx", "n_threads", "max_workers"):
                        self.campos[k].set(str(v))
                    else:
                        self.campos[k].set(v)
                if k in self.campos_bool:
                    self.campos_bool[k].set(bool(v))
            for k, default in DEFAULTS.items():
                if k not in data and k in self.campos:
                    self.campos[k].set(default if not isinstance(default, bool) else "")
                if k not in data and k in self.campos_bool:
                    self.campos_bool[k].set(default)
