#!/usr/bin/env python3
"""
Test de flujo tipo UI: config, rutas, carga de datos y pipeline hasta casos (sin LLM).
Valida que el camino que dispara la UI (config -> datos -> análisis) funciona.
"""
import os
import sys
import tempfile
import json

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.config_loader import load_config, get_config_path, resolve_data_path
from core.preprocess import cargar_chats_as_turns
from core.training import load_training_ffill
from core.cases import extract_no_match_cases
from core.retriever import build_training_index
from core.analyzer import process_one_case
from core.spec import FLOWS_NEUTRALES


def test_config_and_paths():
    """Config se carga y las rutas se resuelven respecto a la raíz."""
    config = load_config()
    path_cfg = get_config_path()
    assert os.path.isabs(path_cfg) or path_cfg
    # Si hay config, debe tener claves esperadas
    if config:
        assert "csv_chats" in config or "output_folder" in config
    # resolve_data_path con relativa
    resolved = resolve_data_path("data/Chat.csv")
    assert "Chat.csv" in resolved or "data" in resolved


def test_full_flow_with_minimal_data():
    """
    Flujo completo como la UI: CSV mínimo -> turns -> training -> cases -> process_one_case.
    Sin leer archivos del disco (salvo temporales); sin LLM.
    """
    csv_chats = """session_id,tipo,texto,intent_detectado
s1,usuario,Quiero ver mi cuenta,
s1,bot,Resumen,Cuentas_Resumen
s1,usuario,El del mes pasado,
s1,bot,NO_MATCH,NO_MATCH
"""
    csv_intents = """Intent Display Name,Language,Phrase
Cuentas_Resumen,es,Quiero ver mi cuenta
,,Resumen de cuenta
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as fc:
        fc.write(csv_chats)
        fc.close()
        path_chats = fc.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as fi:
        fi.write(csv_intents)
        fi.close()
        path_intents = fi.name
    try:
        df_turns = cargar_chats_as_turns(path_chats)
        df_training = load_training_ffill(path_intents)
        assert len(df_turns) == 4
        assert "intent" in df_training.columns or "phrase" in df_training.columns or "Intent Display Name" in df_training.columns

        cases = extract_no_match_cases(df_turns)
        assert len(cases) == 1
        case = cases[0]
        assert case["trigger_user_text"] == "El del mes pasado"

        # Índice mínimo para process_one_case (retriever)
        from core.retriever import build_training_index
        index = build_training_index(df_training)

        result = process_one_case(
            case,
            df_turns,
            index,
            max_msgs=12,
            top_intents=5,
            evidence_per_intent=3,
            neutral_flows=FLOWS_NEUTRALES,
        )
        assert "case_id" in result
        assert "flow_ref" in result
        assert "context_messages" in result
        assert "trigger_user_text" in result
        assert "slot_signals" in result
        assert "candidates" in result
    finally:
        try:
            os.unlink(path_chats)
            os.unlink(path_intents)
        except OSError:
            pass


def test_flow_with_real_data_if_present():
    """
    Si existen data/Chat.csv y data/Intent.csv (config por defecto), cargar y extraer casos.
    No falla si no existen (skip).
    """
    config = load_config()
    path_chats = resolve_data_path(config.get("csv_chats", "data/Chat.csv"))
    path_intents = resolve_data_path(config.get("csv_intents", "data/Intent.csv"))
    if not os.path.isfile(path_chats) or not os.path.isfile(path_intents):
        print("  [SKIP] data/Chat.csv o data/Intent.csv no presentes")
        return
    df_turns = cargar_chats_as_turns(path_chats)
    df_training = load_training_ffill(path_intents)
    cases = extract_no_match_cases(df_turns)
    index = build_training_index(df_training)
    for c in cases[:2]:  # como mucho 2 casos
        r = process_one_case(c, df_turns, index, neutral_flows=FLOWS_NEUTRALES)
        assert "flow_ref" in r and "candidates" in r


if __name__ == "__main__":
    test_config_and_paths()
    test_full_flow_with_minimal_data()
    test_flow_with_real_data_if_present()
    print("test_ui_flow OK")
