"""
Test de ping al LLM: carga el modelo y ejecuta judge_case con payload mínimo.
Solo se ejecuta si hay model_filename configurado y el modelo existe.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_llm_ping():
    """
    Levanta el LLM (si está configurado) y hace un judge_case con payload mínimo.
    Si no hay modelo, omite el test sin fallar.
    """
    try:
        import core.llm_runtime
    except ImportError as e:
        raise RuntimeError(f"No se pudo importar llm_runtime: {e}")

    # Buscar model_filename en config
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "config.json"
    )
    model_filename = None
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        model_filename = cfg.get("model_path") or cfg.get("model_filename") or ""

    if not model_filename or not str(model_filename).strip():
        # Sin modelo configurado: probar solo que el módulo carga
        from core.llm_runtime import extract_json_object, safe_json_loads
        dummy = '{"decision":"AMBIGUOUS","confidence":0.5}'
        obj = safe_json_loads(dummy)
        assert obj["decision"] == "AMBIGUOUS"
        return

    # Verificar que el modelo existe
    try:
        from core.llm_runtime import resolve_model_path, LocalLLM, LLMConfig
        resolve_model_path(model_filename)
    except FileNotFoundError:
        # Modelo no encontrado: OK, no fallar el test
        return

    # Cargar LLM y hacer ping
    cfg = LLMConfig(model_filename=model_filename, n_ctx=512, max_tokens=100)
    llm = LocalLLM(cfg)
    payload = {
        "session_id": "test",
        "case_id": "test:0",
        "flow_ref": "Cuentas",
        "last_valid_intent": "Cuentas_Resumen",
        "context_messages": [{"tipo": "usuario", "texto": "El del mes pasado", "intent": None}],
        "trigger_user_text": "El del mes pasado",
        "slot_signals": ["MONTH_PERIOD"],
        "candidates": [{"intent": "Cuentas_Resumen", "flow": "Cuentas", "score": 0.5, "evidence": []}],
    }
    result = llm.judge_case(payload)
    assert "decision" in result
    assert "confidence" in result
    assert result["decision"] in (
        "MISSED_EXISTING_INTENT_IN_FLOW", "NEW_INTENT_IN_FLOW", "MISSING_PARAMETER_HANDLER",
        "FLOW_SWITCH", "OUT_OF_SCOPE", "AMBIGUOUS",
    )
