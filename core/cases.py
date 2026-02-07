"""
Extracción de casos NO_MATCH: cada fila donde tipo=bot e intent_detectado empieza con NO_MATCH.
"""
import pandas as pd
from typing import List, Dict, Any
from core.preprocess import normalize_text


def extract_no_match_cases(df_turns: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Filtra filas tipo=bot con intent_detectado empezando por NO_MATCH.
    Por cada una construye un case con: case_id, no_match_bot_turn, trigger_user_turn,
    trigger_user_text, trigger_user_text_norm, fecha, session_id.
    """
    cases = []
    df = df_turns.copy()
    df["intent_str"] = df["intent_detectado"].astype(str)
    no_match_mask = df["intent_str"].str.upper().str.startswith("NO_MATCH") & (df["tipo"] == "bot")
    no_match_indices = df.index[no_match_mask].tolist()
    for idx in no_match_indices:
        row = df.loc[idx]
        session_id = row["session_id"]
        turn_index = row.get("turn_index", idx)
        case_id = f"{session_id}:{turn_index}"
        session_df = df[df["session_id"] == session_id].sort_index()
        pos_in_session = session_df.index.get_loc(idx)
        # trigger_user_turn = última fila usuario antes de esta
        trigger_user_text = ""
        trigger_user_text_norm = ""
        trigger_row = None
        trigger_turn_index = None
        for i in range(pos_in_session - 1, -1, -1):
            prev = session_df.iloc[i]
            if str(prev.get("tipo", "")).lower() == "usuario":
                trigger_user_text = str(prev.get("texto", ""))
                trigger_user_text_norm = str(prev.get("texto_norm", "")) or normalize_text(trigger_user_text)
                trigger_row = prev
                trigger_turn_index = prev.get("turn_index", session_df.index[i])
                break
        no_match_bot_turn = row.to_dict()
        cases.append({
            "case_id": case_id,
            "session_id": session_id,
            "fecha": row.get("fecha", ""),
            "no_match_bot_turn": no_match_bot_turn,
            "trigger_user_turn": trigger_row,
            "trigger_turn_index": trigger_turn_index,
            "trigger_user_text": trigger_user_text,
            "trigger_user_text_norm": trigger_user_text_norm,
        })
    return cases
