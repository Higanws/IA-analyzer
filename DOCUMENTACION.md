# 📚 Documentación Técnica - IA Analyzer (Monolito)

Esta documentación explica a fondo el funcionamiento interno, la arquitectura, los módulos y el flujo lógico de la aplicación IA Analyzer monolítica.

---

## 🧠 Objetivo General

Detectar y clasificar errores `NO_MATCH` en conversaciones de chatbot utilizando un modelo de lenguaje (LLM) configurable vía API.

---

## 📁 Estructura de Carpetas

```
IA_Analyzer/
├── app.py                 # Punto de entrada principal
├── core/                  # Lógica interna del análisis
├── views/                 # Interfaz de usuario
├── config/                # Configuración del proyecto
├── data/                  # Entrada/salida CSV
├── style.py               # Estilos visuales
└── build_y_limpiar.bat    # Script de compilación
```

---

## ⚙️ `config/config.json`

Define la configuración base del análisis:

```json
{
  "csv_chats": "data/Chat.csv",
  "csv_intents": "data/Intent.csv",
  "output_folder": "data",
  "llm_url": "http://localhost:11434",
  "llm_id": "qwen2.5-7b-instruct-1m"
}
```

---

## 🧩 Módulos Clave

### `core/analyzer.py`
- Orquesta todo el proceso de análisis
- Ejecuta `construir_prompt(...)` y envía al LLM
- Recibe y valida JSON estructurado
- Guarda los resultados en `data/analisis_no_match.csv`

### `core/preprocess.py`
- Procesa `Chat.csv`
- Agrupa mensajes por sesión
- Estructura útil para análisis

### `core/prompt_builder.py`
- Arma los prompts dinámicamente a partir del historial
- Usa un `PROMPT_BASE` embebido (sin archivo externo)

### `core/mistral_runner.py`
- Abstrae las llamadas HTTP al modelo LLM
- Compatible con OpenAI y modelos locales

### `core/file_manager.py`
- Guarda CSVs asegurando creación de carpetas

---

## 🖼️ Interfaz Gráfica (`views/`)

- `analysis_view.py`: lanza el análisis y muestra consola + tabla
- `chats_view.py`, `intents_view.py`: permiten explorar archivos CSV
- `config_view.py`: edita el archivo de configuración visualmente
- `sidebar.py`: navegación lateral

---

## 🔁 Flujo de Ejecución

1. Usuario abre `IA_Analyzer.exe`
2. Va a la pestaña de "Análisis" y presiona "Iniciar"
3. Se ejecuta `analizar_chats(...)` desde `core/analyzer.py`
4. El progreso aparece en la consola embebida
5. Al finalizar, se muestra el CSV resultante

---

## 🛠 Compilación

Usar el script:

```bash
build_y_limpiar.bat
```

- Compila con PyInstaller
- Limpia `__pycache__` y temporales
- Copia configuración necesaria

---

## 🧪 Casos esperados

- El LLM debe devolver un JSON con:
```json
{
  "motivo_no_match": "...",
  "intents_relevantes": [],
  "mejoras": "",
  "nuevos_ejemplos": []
}
```

- Si no se puede analizar, se marca como `ERROR` en la salida.

---

## 🧱 Dependencias

- pandas
- requests
- tkinter (viene con Python)

