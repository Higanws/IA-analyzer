#!/usr/bin/env python3
"""
Test de ping a la LLM embebida: levanta el modelo (si está configurado) y envía un judge_case mínimo.
Valida que la respuesta tiene decision y confidence. Si no hay modelo, hace skip sin fallar.
"""
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.config_loader import load_config, get_model_filename_from_config
from core.llm_runtime import (
    build_judge_prompt,
    extract_json_object,
    safe_json_loads,
    resolve_model_path,
    LocalLLM,
    LLMConfig,
)
from tests.payloads import get_ping_payload

DECISIONS = (
    "MISSED_EXISTING_INTENT_IN_FLOW",
    "NEW_INTENT_IN_FLOW",
    "MISSING_PARAMETER_HANDLER",
    "FLOW_SWITCH",
    "OUT_OF_SCOPE",
    "AMBIGUOUS",
)


def run_llm_ping():
    print("  [test_llm_ping] Comprobando LLM embebida...")
    config = load_config()
    model_filename = get_model_filename_from_config(config)

    if not model_filename:
        print("  [test_llm_ping] Sin model_path configurado: solo se valida parseo JSON.")
        obj = safe_json_loads('{"decision":"AMBIGUOUS","confidence":0.5}')
        assert obj["decision"] == "AMBIGUOUS"
        assert obj["confidence"] == 0.5
        print("  [test_llm_ping] Parseo OK.")
        return

    try:
        resolve_model_path(model_filename)
    except FileNotFoundError as e:
        print(f"  [test_llm_ping] Modelo no encontrado ({e}). Skip ping real.")
        return

    print(f"  [test_llm_ping] Cargando modelo: {model_filename}")
    try:
        cfg = LLMConfig(model_filename=model_filename, n_ctx=1024, max_tokens=150)
        llm = LocalLLM(cfg)
    except (ImportError, FileNotFoundError, OSError) as e:
        print(f"  [test_llm_ping] No se pudo cargar la LLM ({e}). Skip ping real (instalar llama-cpp-python con librería válida).")
        return

    payload = get_ping_payload()
    prompt = build_judge_prompt(payload)
    print("  [test_llm_ping] --- PROMPT ENVIADO A LA LLM (generado por prompt builder) ---")
    print(prompt)
    print("  [test_llm_ping] --- FIN PROMPT ---")
    print("  [test_llm_ping] Enviando judge_case (ping)...")
    result = llm.judge_case(payload)

    assert "decision" in result, f"Falta 'decision' en respuesta: {result}"
    assert "confidence" in result, f"Falta 'confidence' en respuesta: {result}"
    assert result["decision"] in DECISIONS, f"decision inválida: {result['decision']}"

    print(f"  [test_llm_ping] Respuesta: decision={result['decision']}, confidence={result.get('confidence')}")
    if "why" in result and result["why"]:
        print(f"  [test_llm_ping] why: {result['why'][:80]}...")
    print("  [test_llm_ping] Ping OK.")


if __name__ == "__main__":
    run_llm_ping()
    print("test_llm_ping OK")
