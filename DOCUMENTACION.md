# 📚 Documentación Técnica - IA Analyzer (Monolito)

Esta documentación explica a fondo el funcionamiento interno, la arquitectura, los módulos y el flujo lógico de la aplicación IA Analyzer monolítica.

---

## 🧠 Objetivo General

Detectar y clasificar errores `NO_MATCH` en conversaciones de chatbot utilizando un modelo de lenguaje (LLM) configurable vía API.

---

## 📁 Estructura de Carpetas

```
IA_Analyzer/
├── app.py                 # Punto de entrada principal (GUI)
├── analyzer_cli.py        # CLI pipeline nuevo (--chats, --training, --out)
├── core/                  # Lógica interna
│   ├── analyzer.py        # Orquestador pipeline nuevo (cases + context + retriever + LLM)
│   ├── analyzer_legacy.py # Análisis por sesión vía API
│   ├── spec.py            # Constantes (MAX_MSG_CONTEXT, TOP_INTENTS, FLOWS_NEUTRALES, etc.)
│   ├── preprocess.py      # cargar_chats, cargar_chats_as_turns, normalize_text
│   ├── training.py        # load_training_ffill (training phrases aplanado)
│   ├── cases.py           # extract_no_match_cases
│   ├── context_builder.py # infer_flow_ref, build_context_window
│   ├── retriever.py       # build_training_index, retrieve_candidates (TF-IDF)
│   ├── slot_signals.py    # detect_slot_signals (MONTH, CURRENCY, CARD_TYPE, etc.)
│   ├── llm_runtime.py     # LocalLLM, judge_case (llama-cpp-python)
│   ├── post_validate.py   # Reglas de consistencia, review_flag
│   ├── report_writer.py   # CSV, JSONL, cases_debug
│   ├── prompt_builder.py  # Legacy: construir_prompt, cargar_intents
│   ├── mistral_runner.py  # Legacy: HTTP LLM
│   └── file_manager.py    # guardar_csv
├── views/                 # Interfaz de usuario
├── config/                # Configuración
├── data/                  # Entrada/salida CSV
├── tests/                 # Tests sin pytest: run_tests.py, test_cases, test_context_builder, test_slot_signals, test_llm_runtime, test_llm_ping
└── outputs/               # Salida pipeline nuevo (analisis_no_match.csv, auditoria.jsonl)
```

---

## ⚙️ `config/config.json`

Define la configuración base del análisis:

```json
{
  "csv_chats": "data/Chat.csv",
  "csv_intents": "data/Intent.csv",
  "output_folder": "outputs",
  "llm_url": "http://localhost:11434",
  "llm_id": "qwen2.5-7b-instruct-1m",
  "model_path": "",
  "n_ctx": 4096,
  "n_threads": 8,
  "max_workers": 4,
  "write_debug": false
}
```

- `model_path`: ruta al GGUF para el pipeline local (vacío = solo contexto + retriever + slots, sin LLM).
- `n_ctx`, `n_threads`, `max_workers`: parámetros del LLM local y paralelismo.

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

**Pipeline local con modelo GGUF:** usar `--onedir`; colocar el GGUF en `models/` junto al ejecutable. En `config.json`, `model_path` debe apuntar a la ruta relativa o absoluta del .gguf. Si se empaqueta, `resolve_model_path` en `llm_runtime.py` resuelve rutas relativas al exe.

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
- scikit-learn (retriever TF-IDF en pipeline nuevo)
- llama-cpp-python (LLM embebido en pipeline nuevo)

---

## 🔀 Dos modos de análisis

- **Modo legacy (API):** Botón "Análisis legacy (API)". Análisis por sesión con LLM vía HTTP (Ollama/LM Studio). Config: `llm_url`, `llm_id`. Salida: `analisis_no_match.csv` con motivo_no_match, intents_relevantes, mejoras, nuevos_ejemplos.
- **Modo nuevo (Pipeline local):** Botón "Pipeline nuevo (local)". Análisis por caso NO_MATCH: turnos normalizados, flow_ref, retriever (TF-IDF), slot signals; opcionalmente LLM embebido (GGUF). Requiere **Python free-threaded** (3.13T / 3.14T) para paralelismo real. Config: `csv_chats`, `csv_intents`, `output_folder`, `model_path` (opcional), `n_ctx`, `n_threads`, `max_workers`. Salida en `output_folder`: `analisis_no_match.csv`, `auditoria.jsonl`, opcional `cases_debug/`. Especificación detallada: **Modif/modificacione.md**.

### Uso del CLI (pipeline nuevo)

```bash
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/ --config config/config.json
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/ --no-llm
```

### Formato CSV pipeline nuevo (columnas principales)

fecha, session_id, case_id, mensaje_no_match, bot_no_match_text, flow_ref, last_valid_intent, decision, flow_recommended, intent_top, intents_relevantes, top_evidence, slot_signals, improvements, new_training_phrases, suggested_dialogflow, confidence, review_flag.

---

## 🧪 Tests (scripts .py normales, sin pytest)

Cada test es un script Python ejecutable. Para evitar errores de PowerShell, usar **cmd** o el .bat:

```bash
# Desde cmd (recomendado): ejecutar todos
run_tests.bat

# O manualmente desde la raíz del proyecto
cd IA-analyzer
python tests/run_tests.py

# Ejecutar un test individual
python tests/test_cases.py
python tests/test_context_builder.py
python tests/test_slot_signals.py
python tests/test_llm_runtime.py
python tests/test_llm_ping.py   # Carga el LLM y hace judge_case si hay modelo configurado
```

- **test_cases.py**: extracción de casos NO_MATCH a partir de CSV mínimo
- **test_context_builder.py**: infer_flow_ref y build_context_window
- **test_slot_signals.py**: detect_slot_signals ("Marzo", "dólares", "para mi hijo")
- **test_llm_runtime.py**: parseo JSON del judge (mock)
- **test_llm_ping.py**: levanta el LLM (si model_path está configurado) y ejecuta judge_case

