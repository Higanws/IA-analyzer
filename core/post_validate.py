"""
Post-validación y scoring: umbrales STRONG_MATCH/WEAK_MATCH, reglas de consistencia, review_flag.
"""
from typing import Dict, Any
from core.spec import STRONG_MATCH, WEAK_MATCH


def post_validate(
    llm_result: Dict[str, Any],
    candidates: list,
    flow_ref: str,
    slot_signals: list,
    trigger_user_text: str,
) -> Dict[str, Any]:
    """
    Aplica reglas de consistencia: si STRONG_MATCH en flow_ref y LLM dijo NEW_INTENT -> bajar confianza y review_flag;
    si slot_signals fuerte y trigger corto y LLM no dijo MISSING_PARAMETER_HANDLER -> bajar confianza;
    si evidencias bajas y texto no bancario -> reforzar OUT_OF_SCOPE.
    Devuelve llm_result con confidence y review_flag ajustados.
    """
    result = dict(llm_result)
    decision = (result.get("decision") or "").strip()
    confidence = float(result.get("confidence", 0.5))
    review_flag = False

    # STRONG_MATCH en mismo flow_ref pero LLM dijo NEW_INTENT
    if flow_ref and flow_ref not in ("UNKNOWN", "CHIT"):
        for c in (candidates or []):
            if (c.get("flow") == flow_ref) and any(
                (e.get("sim") or 0) >= STRONG_MATCH for e in (c.get("evidence") or [])
            ):
                if "NEW_INTENT" in decision:
                    confidence = min(confidence, 0.6)
                    review_flag = True
                break

    # slot_signals fuerte + trigger corto y LLM no dijo MISSING_PARAMETER_HANDLER
    trigger_short = len((trigger_user_text or "").strip().split()) <= 4
    if slot_signals and trigger_short and "MISSING_PARAMETER_HANDLER" not in decision:
        confidence = min(confidence, 0.65)
        review_flag = True

    # Sin evidencias > WEAK_MATCH y texto claramente no bancario
    max_sim = 0.0
    for c in (candidates or []):
        for e in (c.get("evidence") or []):
            max_sim = max(max_sim, (e.get("sim") or 0))
    if max_sim < WEAK_MATCH and decision != "OUT_OF_SCOPE":
        # Heurística: palabras muy fuera de dominio
        out_words = {"torta", "futbol", "receta", "clima"}
        if any(w in (trigger_user_text or "").lower() for w in out_words):
            result["decision"] = "OUT_OF_SCOPE"
            result["confidence"] = 0.85
            review_flag = False

    result["confidence"] = round(confidence, 2)
    result["review_flag"] = review_flag
    return result
