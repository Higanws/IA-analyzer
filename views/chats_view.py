# views/chats_view.py

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import json
import os

CONFIG_PATH = "config/config.json"

class ChatsView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#ECECEC")
        tk.Label(self, text="📁 Vista de Chats", font=("Segoe UI", 18), bg="#ECECEC").pack(pady=10)

        self.tabla_frame = tk.Frame(self, bg="#ECECEC")
        self.tabla_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.cargar_datos()

    def cargar_datos(self):
        if not os.path.exists(CONFIG_PATH):
            messagebox.showerror("Error", "No se encontró el archivo de configuración.")
            return

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        csv_path = config.get("csv_chats")
        if not csv_path or not os.path.exists(csv_path):
            messagebox.showerror("Error", "Ruta del CSV de chats no válida o no definida.")
            return

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo CSV: {e}")
            return

        cols = list(df.columns)
        tree = ttk.Treeview(self.tabla_frame, columns=cols, show="headings")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="w")

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
