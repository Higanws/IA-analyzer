"""
Orquestador del pipeline nuevo: casos NO_MATCH, context + retriever + slots en paralelo (ThreadPoolExecutor), LLM judge secuencial.
"""
import os
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

from core.spec import (
    MAX_MSG_CONTEXT,
    TOP_INTENTS,
    EVIDENCE_PER_INTENT,
    FLOWS_NEUTRALES,
    MAX_WORKERS,
)
from core.preprocess import cargar_chats_as_turns
from core.training import load_training_ffill
from core.cases import extract_no_match_cases
from core.context_builder import infer_flow_ref, build_context_window
from core.retriever import build_training_index, retrieve_candidates
from core.slot_signals import detect_slot_signals
from core.post_validate import post_validate
from core.report_writer import write_reports


def process_one_case(
    case: Dict[str, Any],
    df_turns,
    index: Dict[str, Any],
    max_msgs: int = MAX_MSG_CONTEXT,
    top_intents: int = TOP_INTENTS,
    evidence_per_intent: int = EVIDENCE_PER_INTENT,
    neutral_flows: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Por cada case: infer_flow_ref, build_context_window, retrieve_candidates, detect_slot_signals.
    Devuelve payload listo para el judge (y metadatos para el reporte).
    """
    neutral_flows = neutral_flows or FLOWS_NEUTRALES
    trigger_ref = {
        "session_id": case["session_id"],
        "turn_index": case.get("trigger_turn_index"),
    }
    flow_ref, last_valid_intent = infer_flow_ref(
        trigger_ref, df_turns, set(neutral_flows)
    )
    context_messages = build_context_window(
        trigger_ref, df_turns, flow_ref, max_msgs, set(neutral_flows)
    )
    candidates = retrieve_candidates(
        case["trigger_user_text_norm"],
        index,
        flow_ref,
        top_intents=top_intents,
        evidence_per_intent=evidence_per_intent,
    )
    slot_signals = detect_slot_signals(case["trigger_user_text_norm"])
    bot_text = (case.get("no_match_bot_turn") or {}).get("texto", "")
    return {
        "case_id": case["case_id"],
        "session_id": case["session_id"],
        "fecha": case.get("fecha", ""),
        "flow_ref": flow_ref,
        "last_valid_intent": last_valid_intent,
        "context_messages": context_messages,
        "trigger_user_text": case["trigger_user_text"],
        "trigger_user_text_norm": case["trigger_user_text_norm"],
        "slot_signals": slot_signals,
        "candidates": candidates,
        "mensaje_no_match": case["trigger_user_text"],
        "bot_no_match_text": bot_text,
    }


def analizar_pipeline(
    path_chat_csv: str,
    path_training_csv: str,
    path_out: str,
    config: Optional[Dict[str, Any]] = None,
    logger_callback=None,
    use_llm: bool = True,
) -> None:
    """
    Pipeline nuevo: load turns -> training index -> cases -> (paralelo) process_one_case -> (secuencial) LLM judge -> post_validate -> write_reports.
    Si use_llm=False, no se llama al LLM (solo contexto + retriever + slots) y se rellenan decision/confidence por defecto.
    """
    config = config or {}
    if logger_callback:
        logger_callback("Cargando chats como turnos...")
    df_turns = cargar_chats_as_turns(path_chat_csv)
    if logger_callback:
        logger_callback("Cargando training y construyendo índice...")
    df_training = load_training_ffill(path_training_csv)
    index = build_training_index(df_training)
    cases = extract_no_match_cases(df_turns)
    if logger_callback:
        logger_callback(f"Casos NO_MATCH encontrados: {len(cases)}")
    if not cases:
        if logger_callback:
            logger_callback("No hay casos NO_MATCH. Escribiendo reporte vacío.")
        write_reports([], path_out, write_jsonl=config.get("write_jsonl", True), write_debug=config.get("write_debug", False))
        return

    max_workers = config.get("max_workers", MAX_WORKERS)
    max_msgs = config.get("max_msg_context", MAX_MSG_CONTEXT)
    top_int = config.get("top_intents", TOP_INTENTS)
    ev_per = config.get("evidence_per_intent", EVIDENCE_PER_INTENT)
    neutral = config.get("neutral_flows") or FLOWS_NEUTRALES

    def _process(case):
        return process_one_case(case, df_turns, index, max_msgs, top_int, ev_per, neutral)

    payloads = []
    with ThreadPoolExecutor(max_workers=max(1, min(len(cases), max_workers))) as executor:
        for p in executor.map(_process, cases):
            payloads.append(p)

    if use_llm and config.get("model_filename"):
        try:
            from core.llm_runtime import LocalLLM, LLMConfig
            llm_cfg = LLMConfig(
                model_filename=config["model_filename"],
                n_ctx=config.get("n_ctx", 4096),
                n_threads=config.get("n_threads", 8),
                n_batch=config.get("n_batch", 256),
                temperature=config.get("temperature", 0.2),
                max_tokens=config.get("max_tokens", 800),
            )
            llm = LocalLLM(llm_cfg)
        except Exception as e:
            if logger_callback:
                logger_callback(f"No se pudo cargar LLM: {e}. Continuando sin judge.")
            use_llm = False

    rows = []
    for i, payload in enumerate(payloads):
        if logger_callback and (i + 1) % 10 == 0:
            logger_callback(f"Procesando case {i + 1}/{len(payloads)}...")
        if use_llm and config.get("model_filename"):
            try:
                llm_result = llm.judge_case(payload)
                llm_result = post_validate(
                    llm_result,
                    payload.get("candidates", []),
                    payload.get("flow_ref", ""),
                    payload.get("slot_signals", []),
                    payload.get("trigger_user_text", ""),
                )
            except Exception as e:
                llm_result = {
                    "decision": "AMBIGUOUS",
                    "flow_recommended": payload.get("flow_ref", ""),
                    "intent_recommended": [],
                    "intents_relevantes": payload.get("candidates", []),
                    "why": str(e),
                    "improvements": [],
                    "new_training_phrases": {},
                    "suggested_dialogflow": {"parameters": [], "contexts": []},
                    "confidence": 0.0,
                    "review_flag": True,
                }
        else:
            top_candidate = (payload.get("candidates") or [{}])[0]
            llm_result = {
                "decision": "AMBIGUOUS",
                "flow_recommended": payload.get("flow_ref", ""),
                "intent_recommended": [top_candidate.get("intent", "")] if top_candidate else [],
                "intents_relevantes": payload.get("candidates", []),
                "why": "Sin LLM (use_llm=False o model_filename no configurado)",
                "improvements": [],
                "new_training_phrases": {},
                "suggested_dialogflow": {"parameters": [], "contexts": []},
                "confidence": 0.5,
                "review_flag": True,
            }
        row = {
            "fecha": payload.get("fecha", ""),
            "session_id": payload.get("session_id", ""),
            "case_id": payload.get("case_id", ""),
            "mensaje_no_match": payload.get("mensaje_no_match", ""),
            "bot_no_match_text": payload.get("bot_no_match_text", ""),
            "flow_ref": payload.get("flow_ref", ""),
            "last_valid_intent": payload.get("last_valid_intent", ""),
            "decision": llm_result.get("decision", ""),
            "flow_recommended": llm_result.get("flow_recommended", ""),
            "intent_top": (llm_result.get("intent_recommended") or [""])[0] if llm_result.get("intent_recommended") else "",
            "intents_relevantes": json.dumps(llm_result.get("intents_relevantes", []), ensure_ascii=False),
            "top_evidence": json.dumps(
                [(e.get("phrase"), e.get("sim")) for c in (payload.get("candidates") or [])[:1] for e in (c.get("evidence") or [])[:3]],
                ensure_ascii=False,
            ),
            "slot_signals": json.dumps(payload.get("slot_signals", []), ensure_ascii=False),
            "improvements": json.dumps(llm_result.get("improvements", []), ensure_ascii=False),
            "new_training_phrases": json.dumps(llm_result.get("new_training_phrases", {}), ensure_ascii=False),
            "suggested_dialogflow": json.dumps(llm_result.get("suggested_dialogflow", {}), ensure_ascii=False),
            "confidence": llm_result.get("confidence", 0),
            "review_flag": llm_result.get("review_flag", False),
        }
        rows.append(row)

    write_reports(
        rows,
        path_out,
        write_jsonl=config.get("write_jsonl", True),
        write_debug=config.get("write_debug", False),
    )
    if logger_callback:
        logger_callback("Reportes escritos en " + path_out)
