import tkinter as tk

# Colores: normal, hover, seleccionado, hover sobre seleccionado
BG_NORMAL = "#3B4F63"
BG_HOVER = "#4A6280"
BG_SELECTED = "#2E7D32"
BG_SELECTED_HOVER = "#3D9B40"


class Sidebar(tk.Frame):
    def __init__(self, parent, callback):
        super().__init__(parent, bg="#2E3F50", width=200)
        self.callback = callback
        self.selected = None
        self.btns = {}

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
                bg=BG_NORMAL,
                fg="white",
                relief="flat",
                bd=0,
                command=lambda v=vista: self._on_click(v),
                highlightthickness=0,
                padx=10,
                pady=8,
                activebackground=BG_SELECTED,
                activeforeground="white",
            )
            btn.pack(fill="x", padx=12, pady=6)
            btn.bind("<Enter>", lambda e, v=vista: self._on_enter(v))
            btn.bind("<Leave>", lambda e, v=vista: self._on_leave(v))
            self.btns[vista] = btn

    def _on_click(self, vista):
        self.set_selected(vista)
        self.callback(vista)

    def _on_enter(self, vista):
        btn = self.btns.get(vista)
        if not btn:
            return
        if self.selected == vista:
            btn.config(bg=BG_SELECTED_HOVER)
        else:
            btn.config(bg=BG_HOVER)

    def _on_leave(self, vista):
        btn = self.btns.get(vista)
        if not btn:
            return
        if self.selected == vista:
            btn.config(bg=BG_SELECTED)
        else:
            btn.config(bg=BG_NORMAL)

    def set_selected(self, vista):
        if self.selected == vista:
            return
        if self.selected and self.selected in self.btns:
            self.btns[self.selected].config(bg=BG_NORMAL)
        self.selected = vista
        if vista in self.btns:
            self.btns[vista].config(bg=BG_SELECTED)
