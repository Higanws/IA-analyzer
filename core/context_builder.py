"""
Inferencia de flow_ref y construcción de ventana de contexto.
Hacia atrás desde trigger_user_turn; regla de cambio de flow confirmado.
"""
import pandas as pd
from typing import Tuple, List, Dict, Any, Set


def infer_flow_ref(
    trigger_user_turn: Dict[str, Any],
    df_turns: pd.DataFrame,
    neutral_flows: Set[str],
) -> Tuple[str, str]:
    """
    Busca hacia atrás desde trigger_user_turn el último intent válido.
    Devuelve (flow_ref, last_valid_intent_before_no_match).
    Regla: último turn con intent válido y flow no neutral; si no hay, último intent válido (aunque neutral); si no hay ninguno -> UNKNOWN.
    """
    session_id = trigger_user_turn.get("session_id")
    turn_index = trigger_user_turn.get("turn_index", -1)
    if turn_index is None:
        turn_index = -1
    session = df_turns[df_turns["session_id"] == session_id].sort_values("turn_index")
    session = session[session["turn_index"] < turn_index]
    if session.empty:
        return "UNKNOWN", ""
    flow_ref = "UNKNOWN"
    last_valid_intent = ""
    row_with_last_intent = None
    for _, row in session.iloc[::-1].iterrows():
        intent = str(row.get("intent_detectado", "") or "").strip()
        flow = str(row.get("flow_from_intent", "") or "").strip()
        if not intent or flow.upper() == "NO_MATCH":
            continue
        last_valid_intent = intent
        row_with_last_intent = row
        if flow and flow not in neutral_flows:
            flow_ref = flow
            break
        if flow_ref == "UNKNOWN":
            flow_ref = flow or "UNKNOWN"
    if flow_ref == "UNKNOWN" and last_valid_intent and row_with_last_intent is not None:
        flow_ref = (row_with_last_intent.get("flow_from_intent") or "").strip() or "UNKNOWN"
    return flow_ref, last_valid_intent


def build_context_window(
    trigger_user_turn: Dict[str, Any],
    df_turns: pd.DataFrame,
    flow_ref: str,
    max_msgs: int,
    neutral_flows: Set[str],
) -> List[Dict[str, Any]]:
    """
    Ventana hacia atrás desde trigger_user_turn. Máximo max_msgs turnos.
    Corta si "cambio de flow confirmado": 2 intents seguidos con flow != flow_ref y no neutral,
    o 2 de los últimos 3 con flow != flow_ref y no neutral. Neutrales no cuentan como cambio.
    """
    session_id = trigger_user_turn.get("session_id")
    turn_index = trigger_user_turn.get("turn_index", -1)
    if turn_index is None:
        turn_index = -1
    session = df_turns[df_turns["session_id"] == session_id].sort_values("turn_index")
    session = session[session["turn_index"] <= turn_index]
    if session.empty:
        return []
    rows = list(session.iloc[::-1].iterrows())
    context = []
    non_neutral_outliers = 0
    last_three_flows = []
    for i, (_, row) in enumerate(rows):
        if i >= max_msgs:
            break
        flow = str(row.get("flow_from_intent", "") or "").strip()
        intent = str(row.get("intent_detectado", "") or "").strip()
        if flow.upper() == "NO_MATCH":
            continue
        is_neutral = flow in neutral_flows
        if not is_neutral and flow != flow_ref:
            non_neutral_outliers += 1
            last_three_flows.append(1)
        else:
            last_three_flows.append(0)
        if len(last_three_flows) > 3:
            last_three_flows.pop(0)
        if non_neutral_outliers >= 2 or (len(last_three_flows) >= 2 and sum(last_three_flows) >= 2):
            break
        context.append({
            "tipo": row.get("tipo", ""),
            "texto": row.get("texto", ""),
            "intent": intent,
        })
    context.reverse()
    return context
