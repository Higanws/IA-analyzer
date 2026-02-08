import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import pandas as pd

from core.config_loader import load_config, resolve_data_path, get_model_filename_from_config
from core.analyzer import analizar_pipeline

class AnalysisView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ECECEC")
        tk.Label(self, text="🚀 Análisis de Datos", font=("Segoe UI", 18), bg="#ECECEC").pack(pady=10)

        self.console = tk.Text(self, height=15, bg="#1E1E1E", fg="#C0C0C0", insertbackground="white")
        self.console.pack(fill="x", padx=10, pady=5)

        opts_frame = tk.Frame(self, bg="#ECECEC")
        opts_frame.pack(pady=2)
        self.var_informe_agregado = tk.BooleanVar(value=True)
        self.chk_informe_agregado = tk.Checkbutton(
            opts_frame,
            text="Generar informe agregado (fase 2: por flow/intent)",
            variable=self.var_informe_agregado,
            bg="#ECECEC",
            font=("Segoe UI", 10),
        )
        self.chk_informe_agregado.pack(anchor="w")

        btn_frame = tk.Frame(self, bg="#ECECEC")
        btn_frame.pack(pady=5)
        self.btn_analizar = tk.Button(btn_frame, text="Iniciar análisis", bg="#4CAF50", fg="white",
                                     font=("Segoe UI", 12), command=self.ejecutar_analisis)
        self.btn_analizar.pack(side="left", padx=5)

        self.tabla_frame = tk.Frame(self, bg="#ECECEC")
        self.tabla_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, mensaje):
        self.console.insert(tk.END, mensaje + "\n")
        self.console.see(tk.END)

    def ejecutar_analisis(self):
        self.console.delete("1.0", tk.END)
        self.console.insert(tk.END, "Iniciando análisis (pipeline)...\n")
        self.btn_analizar.config(state="disabled", text="Analizando...")
        threading.Thread(target=self._run_pipeline).start()

    def _run_pipeline(self):
        try:
            config = load_config()
            path_out = resolve_data_path(config.get("output_folder", "outputs"))
            model_filename = get_model_filename_from_config(config)
            pipeline_config = {
                "max_workers": config.get("max_workers", 4),
                "model_filename": model_filename or None,
                "n_ctx": config.get("n_ctx", 4096),
                "n_threads": config.get("n_threads", 8),
                "write_jsonl": True,
                "write_debug": config.get("write_debug", False),
                "write_informe_general": self.var_informe_agregado.get(),
            }
            analizar_pipeline(
                path_chat_csv=resolve_data_path(config.get("csv_chats", "")),
                path_training_csv=resolve_data_path(config.get("csv_intents", "")),
                path_out=path_out,
                config=pipeline_config,
                logger_callback=self.log,
                use_llm=bool(model_filename),
            )
            self.log("Listo. Resultado en " + path_out + "\n")
            self._mostrar_resultado_csv(os.path.join(path_out, "analisis_no_match.csv"))
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.btn_analizar.config(state="normal", text="Iniciar análisis")

    def _mostrar_resultado_csv(self, path):
        try:
            path = resolve_data_path(path)
            if not os.path.exists(path):
                return
            df = pd.read_csv(path)
            self.mostrar_resultado_df(df)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar: {e}")

    def mostrar_resultado_df(self, df):
        for widget in self.tabla_frame.winfo_children():
            widget.destroy()
        cols = list(df.columns)
        tree = ttk.Treeview(self.tabla_frame, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="w")
        for _, row in df.iterrows():
            tree.insert("", "end", values=list(row))
        vsb = ttk.Scrollbar(self.tabla_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(self.tabla_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tabla_frame.grid_rowconfigure(0, weight=1)
        self.tabla_frame.grid_columnconfigure(0, weight=1)
        self.console.insert(tk.END, "Resultados cargados.\n")

    def mostrar_resultado(self):
        try:
            config = load_config()
            out_dir = resolve_data_path(config.get("output_folder", "outputs"))
            path = os.path.join(out_dir, "analisis_no_match.csv")
            if not os.path.exists(path):
                raise FileNotFoundError("El análisis falló. No se generó el archivo de salida.")
            df = pd.read_csv(path)
            self.mostrar_resultado_df(df)
            self.console.insert(tk.END, "Resultados cargados correctamente.\n")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el resultado: {e}")
