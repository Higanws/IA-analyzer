# Documentación — IA Analyzer

Documentación técnica del proyecto: **arquitectura**, **especificación del pipeline** y referencias.

Para **levantar el entorno y usar la app** (guía de arranque), ver el [README.md en la raíz](../README.md).

---

## Índice

| Documento | Contenido |
|-----------|-----------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Arquitectura técnica: estructura del proyecto (incl. `entorno/`, `core/`, `views/`), módulos, config, pipeline con/sin LLM, paralelismo (ProcessPool + LLM secuencial), dos fases de salida (por caso e informe agregado), **qué es analyzer_cli**, CLI, tests y compilación a .exe. |
| **[SPEC_PIPELINE.md](SPEC_PIPELINE.md)** | Especificación detallada del pipeline y del juez LLM: objetivo, restricciones, formatos de datos (chat turn, training, case), reglas de inferencia de flow, construcción de contexto, retriever de candidatos, slot signals, prompt del juez, decisiones (NO_MATCH, MISSING_PARAMETER_HANDLER, etc.), post-validación y reportes. |
| **[PLAN_REFACTOR.md](PLAN_REFACTOR.md)** | Plan de refactor ya ejecutado (Fases 1–6); referencia histórica. |

---

## Resumen rápido

- **Pipeline:** Chats CSV + Training CSV → casos NO_MATCH → contexto → retriever (TF-IDF) → slot signals → (opcional) juez LLM → post-validación → reportes (CSV, JSONL, informe general).
- **Fase 1:** Registro detallado por sesión/caso. **Fase 2:** Informe agregado por flow/intent (`informe_general_mejora.json` / `.md`).
- **Entrada por línea de comandos:** **analyzer_cli.py** es la CLI del mismo pipeline que usa la GUI: recibe `--chats`, `--training`, `--out` y opcionalmente `--config` y `--no-llm`. Ver [ARCHITECTURE.md — CLI y analyzer_cli](ARCHITECTURE.md#cli-y-analyzer_cli).
- **Config:** `config/config.json` (rutas, `model_path`, `max_workers`, `write_informe_general`, etc.). Detalle en [ARCHITECTURE.md](ARCHITECTURE.md).
- **Entorno:** Dependencias en un solo `requirements.txt`. Scripts para preparar entorno (instalar deps, modelo GGUF, llama-cpp-python) en **entorno/**; en Windows se usa **preparar_entorno.bat** (menú: instalar LLM, descargar modelo, tests, build).
- **Tests:** `python tests/run_tests.py`; logs en `tests/logs/`. Detalle en [ARCHITECTURE.md](ARCHITECTURE.md).
- **Build .exe:** `preparar_entorno.bat build`; ejecutable en `dist/IA_Analyzer/`; el .gguf va en `dist/IA_Analyzer/models/` y `model_path` en config. Detalle en [ARCHITECTURE.md](ARCHITECTURE.md).
