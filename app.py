import os
import sys
import tkinter as tk
from views.chats_view import ChatsView
from views.intents_view import IntentsView
from views.analysis_view import AnalysisView
from views.config_view import ConfigView
from views.sidebar import Sidebar

# Asegura que se pueda importar desde core/ al compilar como .exe
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS  # PyInstaller lo usa para recursos embebidos
else:
    base_path = os.path.abspath(".")

sys.path.append(os.path.join(base_path, "core"))

class IAAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IA Analyzer")
        self.geometry("1200x720")
        self.configure(bg="#ECECEC")

        self.sidebar = Sidebar(self, self.mostrar_pestana)
        self.sidebar.pack(side="left", fill="y")

        self.main_frame = tk.Frame(self, bg="#ECECEC")
        self.main_frame.pack(side="right", fill="both", expand=True)

        self.pestanas = {
            "chats": ChatsView(self.main_frame),
            "intents": IntentsView(self.main_frame),
            "analysis": AnalysisView(self.main_frame),
            "config": ConfigView(self.main_frame)
        }

        self.pestana_actual = None
        self.mostrar_pestana("chats")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def mostrar_pestana(self, nombre):
        if self.pestana_actual:
            self.pestana_actual.pack_forget()
        self.pestana_actual = self.pestanas[nombre]
        self.pestana_actual.pack(fill="both", expand=True)

    def on_close(self):
        self.destroy()

if __name__ == "__main__":
    app = IAAnalyzerApp()
    app.mainloop()
