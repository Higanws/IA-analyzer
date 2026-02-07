import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import pandas as pd
import json

from core.analyzer_legacy import analizar_chats
from core.analyzer import analizar_pipeline

class AnalysisView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ECECEC")
        tk.Label(self, text="🚀 Análisis de Datos", font=("Segoe UI", 18), bg="#ECECEC").pack(pady=10)

        self.console = tk.Text(self, height=15, bg="#1E1E1E", fg="#C0C0C0", insertbackground="white")
        self.console.pack(fill="x", padx=10, pady=5)

        btn_frame = tk.Frame(self, bg="#ECECEC")
        btn_frame.pack(pady=5)
        self.btn_analizar = tk.Button(btn_frame, text="Análisis legacy (API)", bg="#2196F3", fg="white",
                                       font=("Segoe UI", 12), command=self.ejecutar_analisis)
        self.btn_analizar.pack(side="left", padx=5)
        self.btn_pipeline = tk.Button(btn_frame, text="Pipeline nuevo (local)", bg="#4CAF50", fg="white",
                                       font=("Segoe UI", 12), command=self.ejecutar_pipeline_nuevo)
        self.btn_pipeline.pack(side="left", padx=5)

        self.tabla_frame = tk.Frame(self, bg="#ECECEC")
        self.tabla_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def log(self, mensaje):
        self.console.insert(tk.END, mensaje + "\n")
        self.console.see(tk.END)

    def ejecutar_analisis(self):
        self.console.delete("1.0", tk.END)
        self.console.insert(tk.END, "🔄 Iniciando analisis...\n")
        self.btn_analizar.config(state="disabled", text="Analizando...")
        threading.Thread(target=self.ejecutar_proceso).start()

    def ejecutar_proceso(self):
        try:
            with open("config/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)

            analizar_chats(
                path_chat_csv=config["csv_chats"],
                path_intent_csv=config["csv_intents"],
                path_output_csv=os.path.join(config["output_folder"], "analisis_no_match.csv"),
                llm_url=config["llm_url"],
                llm_id=config["llm_id"],
                logger_callback=self.log
            )

            self.log("✅ Análisis finalizado.\n")
            self.mostrar_resultado()

        except Exception as e:
            self.log(f"❌ Error durante el análisis: {e}")
        finally:
            self.btn_analizar.config(state="normal", text="Análisis legacy (API)")

    def ejecutar_pipeline_nuevo(self):
        self.console.delete("1.0", tk.END)
        self.console.insert(tk.END, "Pipeline nuevo (local)...\n")
        self.btn_pipeline.config(state="disabled", text="Analizando...")
        threading.Thread(target=self._run_pipeline).start()

    def _run_pipeline(self):
        try:
            with open("config/config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            path_out = config.get("output_folder", "outputs")
            pipeline_config = {
                "max_workers": config.get("max_workers"),
                "model_filename": config.get("model_path") or config.get("model_filename"),
                "n_ctx": config.get("n_ctx", 4096),
                "n_threads": config.get("n_threads", 8),
                "write_jsonl": True,
                "write_debug": config.get("write_debug", False),
            }
            analizar_pipeline(
                path_chat_csv=config["csv_chats"],
                path_training_csv=config["csv_intents"],
                path_out=path_out,
                config=pipeline_config,
                logger_callback=self.log,
                use_llm=bool(pipeline_config.get("model_filename")),
            )
            self.log("Listo. Resultado en " + path_out + "\n")
            self._mostrar_resultado_csv(os.path.join(path_out, "analisis_no_match.csv"))
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.btn_pipeline.config(state="normal", text="Pipeline nuevo (local)")

    def _mostrar_resultado_csv(self, path):
        try:
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
            with open("config/config.json", "r", encoding="utf-8") as f:
                path = os.path.join(json.load(f)["output_folder"], "analisis_no_match.csv")
            if not os.path.exists(path):
                raise FileNotFoundError("El análisis falló. No se generó el archivo de salida.")
            df = pd.read_csv(path)
            self.mostrar_resultado_df(df)
            self.console.insert(tk.END, "Resultados cargados correctamente.\n")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el resultado: {e}")
