#!/usr/bin/env python3
"""
Tests de preprocesado: normalize_text, cargar_chats, cargar_chats_as_turns.
Sirven para validar el flujo de datos que usa la UI y el pipeline.
"""
import io
import os
import sys
import tempfile
import pandas as pd

_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _raiz not in sys.path:
    sys.path.insert(0, _raiz)

from core.preprocess import normalize_text, cargar_chats, cargar_chats_as_turns


def test_normalize_text():
    """normalize_text: vacío, acentos, mayúsculas, NaN."""
    assert normalize_text("") == ""
    assert normalize_text("Hola") == "hola"
    assert normalize_text("Qué tal") == "que tal"
    assert normalize_text("  Marzo  ") == "marzo"
    assert normalize_text("DÓLARES") == "dolares"
    assert normalize_text("El del mes pasado") == "el del mes pasado"
    # NaN / no string
    assert normalize_text(pd.NA) == ""
    assert normalize_text(None) == ""


def test_cargar_chats_columnas_renombradas():
    """cargar_chats renombra columnas legacy (cod_wts_jsessionid -> session_id, etc.)."""
    csv = """cod_wts_jsessionid,tipo_mensaje,ds_wts_message,ds_wts_intent
s1,usuario,Hola,
s1,bot,Chau,SALUDO
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv)
        f.close()
    try:
        df = cargar_chats(f.name)
        assert "session_id" in df.columns
        assert "tipo" in df.columns
        assert "texto" in df.columns
        assert "intent_detectado" in df.columns
        assert list(df["texto"]) == ["Hola", "Chau"]
        assert list(df["session_id"]) == ["s1", "s1"]
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


def test_cargar_chats_columnas_directas():
    """cargar_chats acepta CSV con nombres ya estándar (session_id, tipo, texto, intent_detectado)."""
    csv = """session_id,tipo,texto,intent_detectado
s2,usuario,Quiero un prestamo,
s2,bot,Tenemos opciones,Prestamos_Solicitud
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv)
        f.close()
    try:
        df = cargar_chats(f.name)
        assert len(df) == 2
        assert df["tipo"].str.lower().iloc[0] == "usuario"
        assert "fecha" in df.columns  # se añade si no existe
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


def test_cargar_chats_as_turns():
    """cargar_chats_as_turns añade texto_norm, is_no_match, flow_from_intent, turn_index."""
    csv = """session_id,tipo,texto,intent_detectado
s1,usuario,Marzo,
s1,bot,Resumen,Cuentas_Resumen
s1,usuario,El del mes pasado,
s1,bot,NO_MATCH,NO_MATCH
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv)
        f.close()
    try:
        df = cargar_chats_as_turns(f.name)
        assert "texto_norm" in df.columns
        assert "is_no_match" in df.columns
        assert "flow_from_intent" in df.columns
        assert "turn_index" in df.columns
        # Última fila es NO_MATCH
        nm = df[df["is_no_match"]].iloc[0]
        assert nm["texto_norm"] == "no_match"
        assert nm["flow_from_intent"] == "NO_MATCH"
        # Cuentas_Resumen -> flow Cuentas
        cuentas = df[df["intent_detectado"] == "Cuentas_Resumen"].iloc[0]
        assert cuentas["flow_from_intent"] == "Cuentas"
        # turn_index 0,1,2,3
        assert list(df["turn_index"]) == [0, 1, 2, 3]
    finally:
        try:
            os.unlink(f.name)
        except OSError:
            pass


if __name__ == "__main__":
    test_normalize_text()
    test_cargar_chats_columnas_renombradas()
    test_cargar_chats_columnas_directas()
    test_cargar_chats_as_turns()
    print("test_preprocess OK")
