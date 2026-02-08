# IA Analyzer

App de escritorio (**Python + Tkinter**) para analizar conversaciones de chatbot y clasificar errores **NO_MATCH**: pipeline local con retriever (TF-IDF), slots y, opcionalmente, **LLM embebida** (GGUF) como juez.

**Para quien clona el repo:** esta es la guía de arranque. Documentación técnica (arquitectura, especificación del pipeline, qué es analyzer_cli, tests, build) está en **[docs/](docs/README.md)**.

---

## Requisitos

- **Python 3.12+**
- **Pip**

En **Windows** podés usar **preparar_entorno.bat** (doble clic o `preparar_entorno.bat <accion>`). Los scripts que preparan el entorno (deps, modelo, LLM) están en la carpeta **entorno/**.

---

## 1. Preparar entorno (una sola vez)

En la raíz del proyecto:

```bash
python entorno/install_llm.py
```
(El script instala también las dependencias de `requirements.txt`.)

En Windows: **preparar_entorno.bat** → opción **1** (o `preparar_entorno.bat install-llm`).

Ese script (en `entorno/`) instala dependencias si faltan, descarga el modelo GGUF (Qwen 0.5B) en `models/` si no existe, instala `llama-cpp-python` y en Windows aplica el parche para WinError 127 si hace falta. Si no querés usar LLM, dejá `"model_path": ""` en `config/config.json`; el pipeline corre igual.

---

## 2. Ejecutar la app

```bash
python app.py
```

1. En **Configuración** revisá (o editá) rutas de CSV de chats, intents y carpeta de salida.
2. En **Análisis** pulsá **Iniciar análisis**. El progreso se muestra en consola; al terminar se ve la tabla con resultados.

**Por línea de comandos (CLI):** el mismo pipeline se puede ejecutar sin GUI con **analyzer_cli.py** (ver [docs/ — CLI y analyzer_cli](docs/README.md)).

```bash
python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/
```

Con config y LLM: añadí `--config config/config.json`. Sin LLM: `--no-llm`.

---

## Configuración mínima

En `config/config.json`:

| Clave            | Descripción |
|------------------|-------------|
| `csv_chats`      | Ruta al CSV de chats. |
| `csv_intents`    | Ruta al CSV de intents / training phrases. |
| `output_folder`  | Carpeta de salida. |
| `model_path`     | Nombre del .gguf en `models/` (vacío = sin LLM). |

El resto de opciones y la documentación técnica están en **[docs/](docs/README.md)**.

---

## Licencia

Uso interno (Banco Santander). Distribución restringida bajo autorización.
