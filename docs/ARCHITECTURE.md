# Documentación técnica — IA Analyzer

Detalle de arquitectura, módulos, config, pipeline y entradas (GUI y CLI). Especificación detallada del pipeline y del juez LLM: [SPEC_PIPELINE.md](SPEC_PIPELINE.md).

---

## Objetivo

Detectar y clasificar errores **NO_MATCH** en conversaciones de chatbot mediante un pipeline local: casos NO_MATCH → contexto → retriever (TF-IDF) → slot signals → (opcional) juez LLM GGUF → post_validación → reportes CSV/JSONL.

---

## Estructura del proyecto

```
IA-analyzer/
├── app.py                  # Entrada GUI (Tkinter)
├── analyzer_cli.py         # Entrada CLI del mismo pipeline (ver más abajo)
├── preparar_entorno.bat    # Windows: menú (instalar LLM, descargar modelo, tests, build)
├── requirements.txt        # Dependencias únicas (base + huggingface_hub; LLM vía entorno)
├── entorno/                # Scripts para preparar el entorno
│   └── install_llm.py      # Deps + descarga GGUF + llama-cpp-python + parche Win DLL
├── core/                   # Pipeline
│   ├── analyzer.py         # Orquestador (ProcessPool + LLM secuencial)
│   ├── spec.py             # Constantes; ver docs/SPEC_PIPELINE.md
│   ├── preprocess.py       # cargar_chats, cargar_chats_as_turns, normalize_text
│   ├── training.py         # load_training_ffill
│   ├── cases.py            # extract_no_match_cases
│   ├── context_builder.py  # infer_flow_ref, build_context_window
│   ├── retriever.py        # build_training_index, retrieve_candidates (TF-IDF)
│   ├── slot_signals.py     # detect_slot_signals
│   ├── llm_runtime.py      # LocalLLM, judge_case, build_judge_prompt
│   ├── post_validate.py    # Reglas, review_flag
│   ├── report_writer.py    # CSV, JSONL, cases_debug
│   ├── report_aggregate.py # Fase 2: informe general por flow/intent
│   ├── config_loader.py    # get_base_path, load_config, resolve_data_path
│   └── file_manager.py     # guardar_csv
├── views/                  # analysis_view, chats_view, intents_view, config_view, sidebar
├── docs/                    # Documentación (este archivo, SPEC_PIPELINE, PLAN_REFACTOR)
├── config/
├── data/
├── models/                 # Archivos .gguf; model_path = nombre del archivo
├── outputs/
├── bin/                     # Binarios opcionales (no usados por la app; ver bin/README.md)
└── tests/                  # run_tests.py, test_*.py, payloads.py, logs/
```

---

## CLI y analyzer_cli

**analyzer_cli.py** es la entrada por **línea de comandos** al mismo pipeline que usa la interfaz gráfica. Sirve para correr el análisis sin abrir la GUI (scripts, cron, integración).

- **Qué hace:** Carga config (opcional), recibe rutas de CSV de chats y de training, directorio de salida, y opcionalmente desactiva la LLM. Llama a `core.analyzer.analizar_pipeline()` con los mismos datos que usaría la app.
- **Argumentos:**
  - `--chats` (requerido): ruta al CSV de chats.
  - `--training` (requerido): ruta al CSV de intents / training phrases.
  - `--out`: directorio de salida (default: `outputs/`).
  - `--config`: ruta a `config.json` (opcional; si no se pasa, se usa el config por defecto; necesario para usar LLM con `model_path`).
  - `--no-llm`: no usar LLM (solo contexto + retriever + slots; decisiones por defecto).

Ejemplos:

```bash
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/ --config config/config.json
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/ --no-llm
```

---

## Config (`config/config.json`)

| Clave | Descripción |
|-------|-------------|
| **model_path** | Nombre del .gguf en `models/` (vacío = pipeline sin LLM). |
| **n_ctx, n_threads, max_workers** | LLM y paralelismo (procesos en preprocess/prompts). |
| **csv_chats, csv_intents, output_folder** | Entradas y salida. |
| **write_informe_general** | Si es true (por defecto), se escribe el informe agregado (fase 2). |
| **write_debug** | true para escribir `cases_debug/`. |

Resolución de rutas: `core/config_loader.py` (get_base_path, resolve_data_path). En .exe, base = directorio del ejecutable.

---

## Entorno y dependencias

- **Un solo archivo de dependencias:** `requirements.txt` (pandas, requests, scikit-learn, huggingface_hub). La librería **llama-cpp-python** no está en requirements.txt; la instala el script **entorno/install_llm.py** (en Windows con wheel CPU cuando corresponde).
- **Scripts de entorno:** En **entorno/** está `install_llm.py`, que instala dependencias desde la raíz, descarga el GGUF Qwen 0.5B en `models/`, instala llama-cpp-python y en Windows aplica el parche WinError 127 si hace falta. Se ejecuta desde la raíz o vía **preparar_entorno.bat** (opción 1: Instalar LLM; opción 2: solo descargar modelo).

---

## Pipeline: con LLM o sin LLM

- **Sin LLM** (`model_path` vacío): no hace falta `llama-cpp-python`. Decisiones por defecto (AMBIGUOUS, review_flag true).
- **Con LLM**: `llama-cpp-python`, `model_path` con nombre del .gguf en `models/`. El juez devuelve JSON (decision, flow_recommended, intent_recommended, improvements, new_training_phrases, suggested_dialogflow, confidence); luego se aplica post_validate.

Especificación detallada: [SPEC_PIPELINE.md](SPEC_PIPELINE.md).

---

## Paralelismo (sin GIL)

- **Fase paralela 1**: `ProcessPoolExecutor` → preprocess por caso (contexto, retriever, slots).
- **Fase paralela 2**: `ProcessPoolExecutor` → armado de todos los prompts.
- **Fase secuencial**: carga de la LLM y envío de cada prompt de a uno.

---

## Módulos clave

| Módulo | Rol |
|--------|-----|
| **analyzer.py** | Orquesta: carga → casos → (procesos) preprocess + prompts → (secuencial) LLM judge → post_validate → write_reports → write_informe_general (fase 2). |
| **report_aggregate.py** | Fase 2: agrupa filas por flow e intent, consolida mejoras y new_training_phrases, escribe informe_general_mejora.json y .md. |
| **preprocess.py** | cargar_chats, cargar_chats_as_turns (texto_norm, is_no_match, flow_from_intent, turn_index). |
| **llm_runtime.py** | resolve_model_path, build_judge_prompt, LocalLLM (judge_case, chat_json). |
| **config_loader.py** | get_base_path, get_config_path, load_config, resolve_data_path, get_model_filename_from_config. |

---

## Pipeline en dos fases (salidas)

- **Fase 1 — Por sesión/caso**: Se procesa cada NO_MATCH y se clasifica. Salida: **registro detallado** caso a caso (CSV + JSONL).
- **Fase 2 — Agregado**: Se agrupa el registro por **flow** e **intent** y se genera el **informe general de mejora**. Salida: informe_general_mejora.json y .md.

**Output 1 (fase 1)**  
- analisis_no_match.csv, auditoria.jsonl, cases_debug/ (opcional).

**Output 2 (fase 2)**  
- informe_general_mejora.json, informe_general_mejora.md.

---

## Tests

- **test_config.py**, **test_preprocess.py**, **test_prompt_build.py**, **test_ui_flow.py**, **test_llm_runtime.py**, **test_slot_signals.py**, **test_cases.py**, **test_context_builder.py**, **test_llm_ping.py**.

Ejecución: `python tests/run_tests.py`. Logs por test en `tests/logs/`. Validar LLM: `python tests/test_llm_ping.py`. En Windows: **preparar_entorno.bat** → opción 3.

---

## Compilación (.exe)

**preparar_entorno.bat build** (opción 4): PyInstaller con `--onedir`. Ejecutable en `dist/IA_Analyzer/`. Copia `config/` y crea `models/`; colocar el .gguf ahí y `model_path` en config. Las dependencias Python van dentro del .exe; solo el modelo .gguf queda externo.
