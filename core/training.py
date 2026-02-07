"""
Carga y normalización del dataset de entrenamiento (training phrases).
Una fila por (intent, phrase) con intent, flow, language, phrase, phrase_norm, row_id.
"""
import pandas as pd
from core.preprocess import normalize_text


def load_training_ffill(path: str) -> pd.DataFrame:
    """
    Lee CSV de intents (columnas: Intent Display Name, Language, Phrase),
    aplica ffill por intent y devuelve DataFrame aplanado con:
    intent, flow, language, phrase, phrase_norm, row_id.
    """
    df = pd.read_csv(path)
    # Mapeo de nombres alternativos
    col_map = {}
    for c in df.columns:
        c_lower = c.lower().strip()
        if "intent" in c_lower and "display" in c_lower:
            col_map[c] = "intent"
        elif c_lower == "language":
            col_map[c] = "language"
        elif "phrase" in c_lower:
            col_map[c] = "phrase"
    if col_map:
        df = df.rename(columns=col_map)
    if "intent" not in df.columns:
        for cand in ["Intent Display Name", "Intent"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "intent"})
                break
    if "phrase" not in df.columns and "Phrase" in df.columns:
        df = df.rename(columns={"Phrase": "phrase"})
    if "language" not in df.columns and "Language" in df.columns:
        df = df.rename(columns={"Language": "language"})
    df["intent"] = df["intent"].ffill()
    df["phrase"] = df["phrase"].fillna("").astype(str)
    df["language"] = df.get("language", pd.Series(["es"] * len(df))).fillna("es").astype(str)
    df["phrase_norm"] = df["phrase"].map(normalize_text)
    df["flow"] = df["intent"].astype(str).map(lambda x: x.split("_")[0] if "_" in x else x)
    df["row_id"] = range(len(df))
    return df[["intent", "flow", "language", "phrase", "phrase_norm", "row_id"]]
