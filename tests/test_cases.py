"""
Test de extracción de casos NO_MATCH a partir de un CSV de chat mínimo.
"""
import io
import os
import sys
import tempfile
import pandas as pd

# Añadir raíz del proyecto al path (funciona desde raíz o desde tests/)
_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.preprocess import cargar_chats_as_turns
from core.cases import extract_no_match_cases


def test_extract_no_match_cases():
    """Con un Chat.csv mínimo con un NO_MATCH, debe producir un case con trigger_user_text correcto."""
    csv_content = """cod_wts_jsessionid,tipo_mensaje,ds_wts_message,ds_wts_intent
s1,usuario,Hola,
s1,bot,Bienvenido,SALUDO_BIENVENIDA
s1,usuario,Quiero ver mi resumen de cuenta,
s1,bot,NO_MATCH,NO_MATCH
"""
    df = pd.read_csv(io.StringIO(csv_content))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        df.to_csv(f.name, index=False)
        f.close()
        try:
            df_turns = cargar_chats_as_turns(f.name)
        finally:
            try:
                os.unlink(f.name)
            except OSError:
                pass
    cases = extract_no_match_cases(df_turns)
    assert len(cases) == 1
    case = cases[0]
    assert case["trigger_user_text"] == "Quiero ver mi resumen de cuenta"
    assert case["trigger_user_text_norm"] == "quiero ver mi resumen de cuenta"
    assert "s1" in case["case_id"]


if __name__ == "__main__":
    test_extract_no_match_cases()
    print("test_cases OK")
