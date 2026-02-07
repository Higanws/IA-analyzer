#!/usr/bin/env python3
"""
Ejecuta cada script de test como proceso independiente (sin imports entre tests).
Uso: python tests/run_tests.py
     o desde raíz: python tests\run_tests.py
"""
import os
import sys
import subprocess

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_raiz)

SCRIPTS = [
    "tests/test_llm_runtime.py",
    "tests/test_slot_signals.py",
    "tests/test_cases.py",
    "tests/test_context_builder.py",
    "tests/test_llm_ping.py",
]

def main():
    fallos = []
    for script in SCRIPTS:
        path = os.path.join(_raiz, script)
        if not os.path.isfile(path):
            path = script.replace("/", os.sep)
        if not os.path.isfile(path):
            print(f"[SKIP] {script} no encontrado")
            continue
        r = subprocess.run(
            [sys.executable, path],
            cwd=_raiz,
            capture_output=False,
        )
        if r.returncode != 0:
            fallos.append(script)
    if fallos:
        print("\nFallaron:", ", ".join(fallos))
        sys.exit(1)
    print("\nTodos los tests pasaron.")


if __name__ == "__main__":
    main()
