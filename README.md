# 🧠 IA Analyzer (Versión Monolito)

IA Analyzer es una aplicación de escritorio construida con **Python + Tkinter**, diseñada para analizar logs de conversaciones y detectar `NO_MATCH` mediante un modelo LLM externo (local o vía API). Esta versión integra toda la lógica y UI en un único ejecutable `.exe`.

## 📁 Estructura del Proyecto

IA_Analyzer/
├── app.py                     # Punto de entrada principal
├── core/                      # Módulos de backend integrados
│   ├── analyzer.py
│   ├── file_manager.py
│   ├── mistral_runner.py
│   ├── preprocess.py
│   └── prompt_builder.py
├── views/                     # Vistas de la UI
│   ├── analysis_view.py
│   ├── chats_view.py
│   ├── config_view.py
│   ├── intents_view.py
│   └── sidebar.py
├── config/
│   └── config.json
├── data/                      # Archivos .csv de entrada/salida
├── style.py
├── requirements.txt
└── build_y_limpiar.bat        # Script para compilar y limpiar

## ⚙️ Requisitos

- Python 3.12+
- Pip
- Acceso a un modelo LLM vía API (`config.json` lo define)

Instalación de dependencias:

```
pip install -r requirements.txt
```

## 🚀 Uso

1. Configurar `config/config.json` con:

```json
{
  "csv_chats": "data/Chat.csv",
  "csv_intents": "data/Intent.csv",
  "output_folder": "data",
  "llm_url": "http://localhost:11434",
  "llm_id": "qwen2.5-7b-instruct-1m"
}
```

2. Ejecutar la app:

```
python app.py
```

## 🛠 Compilación a `.exe`

Usá el script:

```
build_y_limpiar.bat
```

Esto:
- Compila la app con PyInstaller
- Limpia `__pycache__`, `build/`, `.spec`
- Copia `config.json` al ejecutable final

El ejecutable se generará en:

```
dist/IA_Analyzer/IA_Analyzer.exe
```

## 🧩 Funcionalidades

- ✅ Visualización de archivos `Chat.csv` e `Intent.csv`
- ✅ Forward-fill automático en intents
- ✅ Configuración persistente desde archivo
- ✅ Análisis directo contra modelo LLM
- ✅ Consola integrada en UI
- ✅ Compatible con compilación standalone

## 🔒 Notas

- Esta versión no requiere Python instalado al ejecutarse compilado.
- No escribe archivos de debug.
- Todo está embebido dentro del `.exe`.

## 📬 Licencia

Uso interno (Banco Santander). Distribución restringida bajo autorización.
