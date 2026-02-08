import pandas as pd
import unicodedata


def normalize_text(texto: str) -> str:
    """Normaliza texto para búsqueda: NFKD, ASCII, minúsculas."""
    if not isinstance(texto, str) or pd.isna(texto):
        return ""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("utf-8").lower().strip()


def _flow_from_intent(intent: str) -> str:
    """Parse flow desde intent según spec §4.1."""
    if not intent or not isinstance(intent, str):
        return ""
    intent = intent.strip()
    if intent.upper().startswith("NO_MATCH"):
        return "NO_MATCH"
    if intent.upper().startswith("CHIT_"):
        return "CHIT"
    if "_" in intent:
        return intent.split("_")[0]
    return intent


def cargar_chats(path_chat_csv: str) -> pd.DataFrame:
    df = pd.read_csv(path_chat_csv)

    # Mapeo automático si viene con nombres distintos
    col_map = {
        "cod_wts_jsessionid": "session_id",
        "ds_wts_message": "texto",
        "ds_wts_intent": "intent_detectado",
        "tipo_mensaje": "tipo"
    }
    df.rename(columns=col_map, inplace=True)

    columnas_esperadas = {"session_id", "tipo", "texto", "intent_detectado"}
    if not columnas_esperadas.issubset(df.columns):
        raise ValueError(f"El archivo {path_chat_csv} no contiene las columnas requeridas: {columnas_esperadas}")

    df["session_id"] = df["session_id"].ffill()
    df["intent_detectado"] = df["intent_detectado"].fillna("")
    df["tipo"] = df["tipo"].str.lower()
    if "fecha" not in df.columns:
        df["fecha"] = ""
    return df


def cargar_chats_as_turns(path_chat_csv: str) -> pd.DataFrame:
    """
    Carga chats y devuelve DataFrame con columnas de turno interno:
    session_id, fecha, tipo, texto, texto_norm, intent_detectado, intent_norm,
    is_no_match, flow_from_intent, turn_index.
    """
    df = cargar_chats(path_chat_csv)
    df["texto_norm"] = df["texto"].astype(str).map(normalize_text)
    df["intent_norm"] = df["intent_detectado"].astype(str).map(normalize_text)
    df["is_no_match"] = df["intent_detectado"].astype(str).str.upper().str.startswith("NO_MATCH")
    df["flow_from_intent"] = df["intent_detectado"].astype(str).map(_flow_from_intent)
    df["turn_index"] = df.groupby("session_id").cumcount()
    return df
