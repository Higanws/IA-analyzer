"""
Test de infer_flow_ref y build_context_window con DataFrame de turnos mínimo.
"""
import os
import sys
import pandas as pd

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.context_builder import infer_flow_ref, build_context_window


def test_infer_flow_ref():
    """Infer flow_ref hacia atrás desde trigger; último intent no neutral."""
    df = pd.DataFrame([
        {"session_id": "s1", "turn_index": 0, "tipo": "usuario", "intent_detectado": "", "flow_from_intent": ""},
        {"session_id": "s1", "turn_index": 1, "tipo": "bot", "intent_detectado": "SALUDO_HI", "flow_from_intent": "SALUDO"},
        {"session_id": "s1", "turn_index": 2, "tipo": "usuario", "intent_detectado": "", "flow_from_intent": ""},
        {"session_id": "s1", "turn_index": 3, "tipo": "bot", "intent_detectado": "Cuentas_Resumen", "flow_from_intent": "Cuentas"},
        {"session_id": "s1", "turn_index": 4, "tipo": "usuario", "intent_detectado": "", "flow_from_intent": ""},
    ])
    trigger_ref = {"session_id": "s1", "turn_index": 4}
    neutral = {"SALUDO", "CHIT", "GENERIC", "NO_MATCH"}
    flow_ref, last_valid = infer_flow_ref(trigger_ref, df, neutral)
    assert flow_ref == "Cuentas"
    assert last_valid == "Cuentas_Resumen"


def test_build_context_window():
    """Ventana hacia atrás con límite max_msgs y regla de cambio de flow."""
    df = pd.DataFrame([
        {"session_id": "s1", "turn_index": 0, "tipo": "usuario", "texto": "Hola", "intent_detectado": "", "flow_from_intent": ""},
        {"session_id": "s1", "turn_index": 1, "tipo": "bot", "texto": "Bienvenido", "intent_detectado": "SALUDO_HI", "flow_from_intent": "SALUDO"},
        {"session_id": "s1", "turn_index": 2, "tipo": "usuario", "texto": "Quiero ver cuenta", "intent_detectado": "", "flow_from_intent": ""},
        {"session_id": "s1", "turn_index": 3, "tipo": "bot", "texto": "OK", "intent_detectado": "Cuentas_Resumen", "flow_from_intent": "Cuentas"},
        {"session_id": "s1", "turn_index": 4, "tipo": "usuario", "texto": "El del mes pasado", "intent_detectado": "", "flow_from_intent": ""},
    ])
    trigger_ref = {"session_id": "s1", "turn_index": 4}
    neutral = {"SALUDO", "CHIT", "GENERIC", "NO_MATCH"}
    ctx = build_context_window(trigger_ref, df, "Cuentas", max_msgs=12, neutral_flows=neutral)
    assert len(ctx) >= 1
    assert any(m.get("texto") == "El del mes pasado" for m in ctx)


if __name__ == "__main__":
    test_infer_flow_ref()
    test_build_context_window()
    print("test_context_builder OK")
