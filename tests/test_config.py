#!/usr/bin/env python3
"""
Comprueba que config/config.json existe y tiene las claves esperadas (sin borrar claves al guardar).
"""
import sys
import os

# Asegurar raíz del proyecto en path
_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.config_loader import load_config, get_config_path, get_model_filename_from_config, resolve_data_path

CLAVES_ESPERADAS = [
    "csv_chats", "csv_intents", "output_folder",
    "model_path", "n_ctx", "n_threads", "max_workers", "write_debug",
]

def main():
    if not os.path.isfile(get_config_path()):
        print("OK (skip): no existe config, no se puede validar")
        return 0
    config = load_config()
    if not config:
        print("ERROR: config vacío")
        return 1
    faltan = [k for k in CLAVES_ESPERADAS if k not in config]
    if faltan:
        print("ERROR: faltan claves en config:", faltan)
        return 1
    # Normalización model_path
    m = get_model_filename_from_config(config)
    if config.get("model_path") and not m:
        print("ERROR: model_path tiene valor pero get_model_filename_from_config devolvió vacío")
        return 1
    print("OK: config con claves esperadas, get_model_filename_from_config OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
