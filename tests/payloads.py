"""
Payload compartido para tests: mismo caso y mismo prompt en prompt_build y llm_ping.

evidence: por cada candidato, lista de {phrase, sim} con las frases de entrenamiento
de ese intent que más se parecieron al trigger_user_text (TF-IDF), y su similitud.
El retriever real llena esto en retrieve_candidates().
"""
from typing import Any, Dict, List


def get_ping_payload() -> Dict[str, Any]:
    """
    Payload de ping: caso Cuentas + "El del mes pasado".
    Usado por test_prompt_build (log del prompt armado) y test_llm_ping (envío a la LLM).
    Así el prompt que genera el prompt builder es el mismo que se envía a la LLM.
    """
    return {
        "session_id": "ping",
        "case_id": "ping:0",
        "flow_ref": "Cuentas",
        "last_valid_intent": "Cuentas_Resumen",
        "context_messages": [{"tipo": "usuario", "texto": "El del mes pasado", "intent": None}],
        "trigger_user_text": "El del mes pasado",
        "slot_signals": ["MONTH_PERIOD"],
        "candidates": [
            {
                "intent": "Cuentas_Resumen",
                "flow": "Cuentas",
                "score": 0.5,
                "evidence": [
                    {"phrase": "Ver movimientos de mi cuenta", "sim": 0.38},
                    {"phrase": "Resumen de mi cuenta", "sim": 0.31},
                    {"phrase": "Estado de cuenta", "sim": 0.25},
                ],
                "training_phrases": [
                    "Quiero ver el resumen de mi cuenta",
                    "Resumen de mi cuenta",
                    "Ver movimientos de mi cuenta",
                    "Estado de cuenta",
                ],
            },
        ],
    }
