"""
Test de parseo JSON del judge (respuesta mock).
"""
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.llm_runtime import extract_json_object, safe_json_loads


def test_extract_json_object_plain():
    """Extrae JSON objeto de texto plano."""
    text = 'Aquí está la respuesta: {"decision": "NEW_INTENT_IN_FLOW", "confidence": 0.8}'
    obj_str = extract_json_object(text)
    assert "decision" in obj_str
    obj = safe_json_loads(text)
    assert obj["decision"] == "NEW_INTENT_IN_FLOW"
    assert obj["confidence"] == 0.8


def test_extract_json_object_markdown():
    """Extrae JSON de bloque markdown con ```."""
    text = '''```json
{"decision": "MISSING_PARAMETER_HANDLER", "flow_recommended": "Cuentas"}
```'''
    obj = safe_json_loads(text)
    assert obj["decision"] == "MISSING_PARAMETER_HANDLER"
    assert obj["flow_recommended"] == "Cuentas"


def test_extract_json_object_nested():
    """Extrae JSON con objetos anidados."""
    text = '''Pensando... {"decision": "OUT_OF_SCOPE", "intents_relevantes": [{"intent": "X", "score": 0.5}], "confidence": 0.9}'''
    obj = safe_json_loads(text)
    assert obj["decision"] == "OUT_OF_SCOPE"
    assert len(obj["intents_relevantes"]) == 1
    assert obj["intents_relevantes"][0]["intent"] == "X"


if __name__ == "__main__":
    test_extract_json_object_plain()
    test_extract_json_object_markdown()
    test_extract_json_object_nested()
    print("test_llm_runtime OK")
