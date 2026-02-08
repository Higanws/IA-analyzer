#!/usr/bin/env python3
"""
Tests del armado de prompt para el juez LLM (build_judge_prompt).
Verifica que el prompt incluye instrucciones, schema y el payload de entrada.
"""
import json
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.llm_runtime import build_judge_prompt, JSON_SCHEMA_HINT
from tests.payloads import get_ping_payload


def test_build_judge_prompt_contains_instructions():
    """El prompt debe contener la tarea y las reglas."""
    payload = {"session_id": "s1", "trigger_user_text": "Marzo", "flow_ref": "Cuentas"}
    prompt = build_judge_prompt(payload)
    assert "Tarea: clasificar el NO_MATCH" in prompt
    assert "MISSING_PARAMETER_HANDLER" in prompt
    assert "MISSED_EXISTING_INTENT_IN_FLOW" in prompt
    assert "OUT_OF_SCOPE" in prompt


def test_build_judge_prompt_contains_schema():
    """El prompt debe incluir el schema (decision, confidence, etc.)."""
    payload = {"session_id": "s1"}
    prompt = build_judge_prompt(payload)
    assert "decision" in prompt
    assert "confidence" in prompt
    assert "flow_recommended" in prompt
    assert "intents_relevantes" in prompt


def test_build_judge_prompt_contains_input():
    """El prompt debe incluir el payload como INPUT."""
    payload = {
        "session_id": "ping",
        "case_id": "ping:0",
        "flow_ref": "Prestamos",
        "trigger_user_text": "Cuánto me pueden dar?",
        "slot_signals": ["AMOUNT_QUERY"],
        "candidates": [
            {"intent": "Prestamos_Solicitud", "flow": "Prestamos", "score": 0.6, "evidence": [], "training_phrases": ["Quiero solicitar un préstamo", "Necesito un préstamo personal"]},
        ],
    }
    prompt = build_judge_prompt(payload)
    assert "INPUT:" in prompt
    assert "ping" in prompt
    assert "Cuánto me pueden dar?" in prompt
    assert "AMOUNT_QUERY" in prompt
    assert "Prestamos" in prompt
    # El payload serializado debe ser JSON válido dentro del prompt
    idx = prompt.find("INPUT:")
    rest = prompt[idx + len("INPUT:"):].strip()
    # Puede haber un JSON en la siguiente línea
    obj = json.loads(rest)
    assert obj["session_id"] == "ping"
    assert obj["trigger_user_text"] == "Cuánto me pueden dar?"


def test_json_schema_hint_has_expected_keys():
    """JSON_SCHEMA_HINT debe tener las claves que el judge debe devolver."""
    expected = {"decision", "flow_recommended", "intent_recommended", "intents_relevantes",
                "why", "improvements", "new_training_phrases", "suggested_dialogflow", "confidence"}
    assert set(JSON_SCHEMA_HINT.keys()) >= expected


def log_prompt_armado():
    """Escribe en salida (log) el prompt armado para el caso de ping (mismo que usa test_llm_ping)."""
    payload = get_ping_payload()
    prompt = build_judge_prompt(payload)
    print("  [test_prompt_build] --- PROMPT ARMADO (ejemplo de análisis) ---")
    print(prompt)
    print("  [test_prompt_build] --- FIN PROMPT ARMADO ---")


if __name__ == "__main__":
    test_build_judge_prompt_contains_instructions()
    test_build_judge_prompt_contains_schema()
    test_build_judge_prompt_contains_input()
    test_json_schema_hint_has_expected_keys()
    log_prompt_armado()
    print("test_prompt_build OK")
