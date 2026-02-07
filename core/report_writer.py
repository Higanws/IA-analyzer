"""
Escritura de reportes: CSV (§11.1), JSONL auditoría, opcional cases_debug.
"""
import os
import json
import pandas as pd
from typing import List, Dict, Any
from core.file_manager import guardar_csv


CSV_COLUMNS = [
    "fecha", "session_id", "case_id", "mensaje_no_match", "bot_no_match_text",
    "flow_ref", "last_valid_intent", "decision", "flow_recommended", "intent_top",
    "intents_relevantes", "top_evidence", "slot_signals", "improvements",
    "new_training_phrases", "suggested_dialogflow", "confidence", "review_flag",
]


def write_reports(
    rows: List[Dict[str, Any]],
    path_out_dir: str,
    write_jsonl: bool = True,
    write_debug: bool = False,
) -> None:
    """
    Escribe CSV con columnas §11.1, opcional JSONL y opcional carpeta cases_debug.
    """
    os.makedirs(path_out_dir, exist_ok=True)
    csv_path = os.path.join(path_out_dir, "analisis_no_match.csv")
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=CSV_COLUMNS)
    guardar_csv(df, csv_path)
    if write_jsonl:
        jsonl_path = os.path.join(path_out_dir, "auditoria.jsonl")
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    if write_debug:
        debug_dir = os.path.join(path_out_dir, "cases_debug")
        os.makedirs(debug_dir, exist_ok=True)
        for r in rows:
            case_id = (r.get("case_id") or "unknown").replace(":", "_")
            p = os.path.join(debug_dir, f"{case_id}.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=2)
