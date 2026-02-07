"""
Detección de señales de slot/parámetro (Dialogflow entities).
Regex por: MONTH/PERIOD, CURRENCY, CARD_TYPE, RELATION_MINOR, AMOUNT_QUERY.
"""
import re
from typing import List

# Regex por slot según spec §8.1
SLOT_PATTERNS = {
    "MONTH_PERIOD": [
        re.compile(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b", re.I),
        re.compile(r"\b(mes\s+pasado|mes\s+anterior|último\s+mes|este\s+mes)\b", re.I),
    ],
    "CURRENCY": [
        re.compile(r"\b(usd|u\$s|d[oó]lar(?:es)?)\b", re.I),
    ],
    "CARD_TYPE": [
        re.compile(r"\b(adicional|titular|suplementaria)\b", re.I),
    ],
    "RELATION_MINOR": [
        re.compile(r"\b(hijo|hija|menor|menor\s+de\s+edad|tutor)\b", re.I),
    ],
    "AMOUNT_QUERY": [
        re.compile(r"\b(cu[aá]nto|monto|m[aá]ximo|hasta)\b", re.I),
    ],
}


def detect_slot_signals(trigger_user_text_norm: str) -> List[str]:
    """
    Devuelve lista de nombres de slots detectados en el texto normalizado.
    """
    if not trigger_user_text_norm or not isinstance(trigger_user_text_norm, str):
        return []
    text = trigger_user_text_norm.strip()
    if not text:
        return []
    signals = []
    for slot_name, patterns in SLOT_PATTERNS.items():
        for pat in patterns:
            if pat.search(text):
                signals.append(slot_name)
                break
    return signals
