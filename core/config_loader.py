"""
Rutas y carga de configuración. Una sola fuente de verdad para base_path,
ruta del config y resolución de rutas de datos (relativas al base_path).
Funciona en desarrollo (CWD = raíz del proyecto) y empaquetado (.exe).
"""
import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, Optional


def get_base_path() -> str:
    """
    Raíz desde la que se resuelven config y datos.
    - Empaquetado (frozen): directorio del ejecutable (config/ y data/ junto al .exe).
    - Desarrollo: directorio del script (argv[0]); si está en subcarpeta (ej. tests/), sube a la raíz que contiene core/.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    if getattr(sys, "argv", None) and sys.argv:
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
        # Si estamos en tests/ o en otra subcarpeta, la raíz del proyecto es el padre que tiene core/
        parent = os.path.dirname(base)
        if not os.path.isdir(os.path.join(base, "core")) and os.path.isdir(os.path.join(parent, "core")):
            base = parent
        return base
    return os.path.abspath(".")


def get_config_path() -> str:
    """Ruta absoluta al archivo config/config.json."""
    base = get_base_path()
    return os.path.join(base, "config", "config.json")


def resolve_data_path(relative_path: str) -> str:
    """
    Convierte una ruta relativa (ej. data/Chat.csv) en absoluta respecto a base_path.
    Si relative_path ya es absoluta, se devuelve normalizada.
    """
    path = relative_path.strip()
    if os.path.isabs(path):
        return os.path.normpath(path)
    base = get_base_path()
    return os.path.normpath(os.path.join(base, path))


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carga el JSON de configuración. Si path es None, usa get_config_path().
    Devuelve dict vacío si el archivo no existe.
    """
    config_path = path or get_config_path()
    if not os.path.isfile(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_model_filename_from_config(config: Dict[str, Any]) -> str:
    """
    Unifica lectura de modelo GGUF: en JSON está como model_path.
    Devuelve cadena vacía si no hay modelo configurado.
    """
    return (config.get("model_path") or config.get("model_filename") or "").strip()
