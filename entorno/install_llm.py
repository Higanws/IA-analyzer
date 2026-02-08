#!/usr/bin/env python3
"""
Preparar entorno: un solo script para dejar la app lista.

- Dependencias (requirements.txt en la raíz del proyecto)
- Descarga del GGUF Qwen 0.5B en models/ (si no existe)
- llama-cpp-python (en Windows: wheel CPU precompilado; si falla, indica Build Tools)
- En Windows: parche WinError 127 (DLL) si hace falta

Debe ejecutarse desde la raíz del repo o vía preparar_entorno.bat.
"""
import argparse
import subprocess
import sys
import os
import pathlib

# Raíz del proyecto (carpeta que contiene entorno/, app.py, requirements.txt)
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ROOT = _SCRIPT_DIR.parent

REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
FILENAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"


def run(cmd, desc):
    print(f"\n>>> {desc}")
    print(f"    {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=str(ROOT))
    return r.returncode == 0


def download_gguf(root):
    """Descarga el GGUF de Qwen 0.5B a models/ (idempotente)."""
    root = pathlib.Path(root)
    models_dir = root / "models"
    models_dir.mkdir(exist_ok=True)
    out_path = models_dir / FILENAME
    if out_path.is_file():
        print(f"Ya existe: {out_path}")
        print(f"En config.json usa: \"model_path\": \"{FILENAME}\"")
        return 0
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("Instalando huggingface_hub...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"], check=False, cwd=str(ROOT))
        from huggingface_hub import hf_hub_download
    print(f"Descargando {REPO} -> {FILENAME} (~490 MB)...")
    sys.stdout.flush()
    hf_hub_download(repo_id=REPO, filename=FILENAME, local_dir=str(models_dir))
    print(f"Listo: {out_path}")
    print(f"En config/config.json: \"model_path\": \"{FILENAME}\"")
    return 0


def apply_win_dll_fix():
    """Parche WinError 127: quitar winmode=RTLD_GLOBAL en la carga de la DLL de llama-cpp-python."""
    import site
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        base = pathlib.Path(sp) / "llama_cpp"
        if (base / "_ctypes_extensions.py").exists():
            break
    else:
        return False
    ctypes_file = base / "_ctypes_extensions.py"
    text = ctypes_file.read_text(encoding="utf-8")
    line = '        cdll_args["winmode"] = ctypes.RTLD_GLOBAL'
    if line not in text:
        if "# cdll_args" in text and "RTLD_GLOBAL" in text:
            print("Parche Win (DLL) ya aplicado.")
            return True
        return False
    new_text = text.replace(
        line,
        '        # cdll_args["winmode"] = ctypes.RTLD_GLOBAL  # desactivado: evita WinError 127 en Windows',
    )
    ctypes_file.write_text(new_text, encoding="utf-8")
    print("Parche Win (DLL) aplicado. Probá: python -c \"from llama_cpp import Llama; print('OK')\"")
    return True


def main():
    parser = argparse.ArgumentParser(description="Preparar entorno (deps + modelo + llama-cpp-python)")
    parser.add_argument("--download-only", action="store_true", help="Solo descargar el modelo GGUF a models/")
    args = parser.parse_args()

    root = str(ROOT)
    os.chdir(root)

    if args.download_only:
        return 0 if download_gguf(root) == 0 else 1

    print("Preparando entorno (deps + modelo + llama-cpp-python)...")

    # 1. Dependencias (requirements.txt en la raíz)
    req_path = os.path.join(root, "requirements.txt")
    if not os.path.isfile(req_path):
        print(f"No se encontró {req_path}. Ejecutá desde la raíz del proyecto.")
        return 1
    if not run(f'"{sys.executable}" -m pip install -q -r requirements.txt', "1/4 Dependencias (requirements.txt)"):
        print("Error instalando dependencias.")
        return 1

    # 2. Descarga del modelo
    download_gguf(root)

    # 3. llama-cpp-python (wheel CPU precompilado primero)
    print("\n>>> 3/4 Instalando llama-cpp-python (wheel CPU precompilado)...")
    cpu_whl_url = "https://abetlen.github.io/llama-cpp-python/whl/cpu"
    ok = subprocess.run(
        [sys.executable, "-m", "pip", "install", "llama-cpp-python",
         "--only-binary=:all:", "--extra-index-url", cpu_whl_url],
        shell=False,
    ).returncode == 0
    if not ok:
        print("No hay wheel para tu Python; intentando desde fuente...")
        ok = subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python"], shell=False).returncode == 0
    if not ok:
        print("""
*** llama-cpp-python no se pudo instalar.

En Windows sin compilador: instalá "Build Tools para Visual Studio"
(https://visualstudio.microsoft.com/visual-cpp-build-tools/) con
"Desarrollo para el escritorio con C++", reiniciá la terminal y ejecutá:
  pip install llama-cpp-python

Si usaste el wheel y al importar falla con WinError 127: instalá
"Visual C++ Redistributable" (https://aka.ms/vs/17/release/vc_redist.x64.exe).
""")
        return 0

    # 4. En Windows: parche WinError 127 (DLL)
    if sys.platform == "win32":
        print("\n>>> 4/4 Windows: aplicando parche DLL si hace falta...")
        if not apply_win_dll_fix():
            print("(Parche no aplicado o no necesario; si ves WinError 127, ejecutá el Redistributable.)")
    else:
        print("\n>>> 4/4 Listo (no Windows, sin parche DLL).")

    print("\nEntorno listo. Ejecutá: python app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
