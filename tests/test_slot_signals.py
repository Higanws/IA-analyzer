"""
Test de detect_slot_signals con frases: Marzo, dólares, para mi hijo.
"""
import os
import sys

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.preprocess import normalize_text
from core.slot_signals import detect_slot_signals


def test_slot_signals_marzo():
    """'Marzo' debe detectar MONTH_PERIOD."""
    text = normalize_text("Marzo")
    signals = detect_slot_signals(text)
    assert "MONTH_PERIOD" in signals


def test_slot_signals_dolares():
    """'dólares' debe detectar CURRENCY."""
    text = normalize_text("dólares")
    signals = detect_slot_signals(text)
    assert "CURRENCY" in signals


def test_slot_signals_para_mi_hijo():
    """'para mi hijo' debe detectar RELATION_MINOR."""
    text = normalize_text("para mi hijo")
    signals = detect_slot_signals(text)
    assert "RELATION_MINOR" in signals


def test_slot_signals_cuanto():
    """'cuánto' debe detectar AMOUNT_QUERY."""
    text = normalize_text("cuánto me pueden dar")
    signals = detect_slot_signals(text)
    assert "AMOUNT_QUERY" in signals


def test_slot_signals_adicional():
    """'adicional' debe detectar CARD_TYPE."""
    text = normalize_text("tarjeta adicional")
    signals = detect_slot_signals(text)
    assert "CARD_TYPE" in signals


if __name__ == "__main__":
    test_slot_signals_marzo()
    test_slot_signals_dolares()
    test_slot_signals_para_mi_hijo()
    test_slot_signals_cuanto()
    test_slot_signals_adicional()
    print("test_slot_signals OK")
