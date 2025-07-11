import tkinter as tk

class Sidebar(tk.Frame):
    def __init__(self, parent, callback):
        super().__init__(parent, bg="#2E3F50", width=200)
        self.callback = callback

        self.logo = tk.Label(self, text="🧠 IA Analyzer", bg="#2E3F50", fg="white", font=("Segoe UI", 16, "bold"))
        self.logo.pack(pady=20)

        botones = [
            ("📁 Ver Chats", "chats"),
            ("📄 Ver Intents", "intents"),
            ("🚀 Análisis", "analysis"),
            ("⚙️ Configuración", "config")
        ]

        for texto, vista in botones:
            btn = tk.Button(
                self,
                text=texto,
                font=("Segoe UI", 12),
                bg="#3B4F63",
                fg="white",
                relief="flat",
                bd=0,
                command=lambda v=vista: callback(v),
                highlightthickness=0,
                padx=10,
                pady=8
            )
            btn.pack(fill="x", padx=12, pady=6)
