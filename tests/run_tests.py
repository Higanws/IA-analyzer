#!/usr/bin/env python3
"""
Ejecuta cada script de test como proceso independiente (sin imports entre tests).
Fija la raíz del proyecto en CWD y en sys.path para que los tests encuentren core/ y config.
Guarda logs en tests/logs/ (un .log por test y un run_<timestamp>.log con todo el run).

Uso: python tests/run_tests.py  (desde raíz o desde tests/)
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_raiz)
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

LOGS_DIR = Path(_raiz) / "tests" / "logs"

SCRIPTS = [
    "tests/test_config.py",
    "tests/test_preprocess.py",
    "tests/test_prompt_build.py",
    "tests/test_ui_flow.py",
    "tests/test_llm_runtime.py",
    "tests/test_slot_signals.py",
    "tests/test_cases.py",
    "tests/test_context_builder.py",
    "tests/test_llm_ping.py",
]


def main():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_log_path = LOGS_DIR / f"run_{run_ts}.log"
    run_lines = []

    def log(msg: str):
        run_lines.append(msg)
        print(msg, flush=True)

    fallos = []
    for i, script in enumerate(SCRIPTS):
        path = os.path.join(_raiz, script)
        if not os.path.isfile(path):
            path = script.replace("/", os.sep)
        if not os.path.isfile(path):
            log(f"[SKIP] {script} no encontrado")
            continue
        sep = "=" * 60
        log(f"\n{sep}\n  [{i+1}/{len(SCRIPTS)}] {script}\n{sep}")
        r = subprocess.run(
            [sys.executable, path],
            cwd=_raiz,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out:
            log(out)
        if err:
            log(err)
        # Log por test individual
        base = os.path.splitext(os.path.basename(script))[0]
        per_file = LOGS_DIR / f"{base}.log"
        with open(per_file, "w", encoding="utf-8") as f:
            f.write(f"# {script} @ {datetime.now().isoformat()}\n")
            f.write(f"# exitcode={r.returncode}\n\n")
            if out:
                f.write(out + "\n")
            if err:
                f.write(err + "\n")
        if r.returncode != 0:
            fallos.append(script)
            log(f"[FAIL] {script} -> exit {r.returncode}")

    if fallos:
        log("\nFallaron: " + ", ".join(fallos))
        run_lines.append("\nFallaron: " + ", ".join(fallos))
    else:
        log("\nTodos los tests pasaron.")
        run_lines.append("\nTodos los tests pasaron.")

    with open(run_log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(run_lines))
    log(f"\nLogs guardados en: {LOGS_DIR.resolve()}")
    log(f"  - Por test: test_*.log (un archivo por script)")
    log(f"  - Run completo: run_{run_ts}.log")

    if fallos:
        sys.exit(1)


if __name__ == "__main__":
    main()
