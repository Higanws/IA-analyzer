# Scripts de entorno

Scripts para **preparar el entorno** (dependencias, modelo GGUF, LLM). Se ejecutan desde la **raíz del proyecto** o vía **preparar_entorno.bat** en Windows.

| Script | Descripción |
|--------|-------------|
| **install_llm.py** | Instala `requirements.txt`, descarga el GGUF Qwen 0.5B en `models/`, instala `llama-cpp-python` (en Windows con wheel CPU) y aplica el parche WinError 127 si hace falta. Opción `--download-only` para solo descargar el modelo. |

Desde la raíz: `python entorno/install_llm.py` (o `preparar_entorno.bat` → opción 1).
