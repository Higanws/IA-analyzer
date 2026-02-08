"""
Fase 2: agregar registros post-análisis por flow/intent y escribir informe general de mejora.

Toma las filas del registro caso a caso (fase 1), agrupa por flow_ref y por intent_top,
consolida mejoras y new_training_phrases, y escribe informe_general_mejora.json y .md.

Opcional futuro: pasar el informe agregado (por_flow, por_intent) a una segunda llamada LLM
con prompt tipo "Generá un informe narrativo de mejoras para Dialogflow" y añadir
esa sección al .md o a un informe_general_narrativo.txt.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any, Dict, List


def _safe_load_json(s: Any, default: Any = None):
    if default is None:
        default = {} if isinstance(s, str) and s.strip().startswith("{") else []
    if s is None or s == "":
        return default
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default


def aggregate_by_flow(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrupa por flow_ref. Por cada flow: cantidad, decisiones, mensajes, improvements y new_training_phrases consolidados."""
    by_flow: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        flow = (r.get("flow_ref") or "").strip() or "UNKNOWN"
        by_flow[flow].append(r)

    result = {}
    for flow, group in sorted(by_flow.items()):
        decisions = []
        mensajes = []
        improvements_all: List[str] = []
        new_training_merged: Dict[str, List[str]] = {}
        intent_counts: Dict[str, int] = defaultdict(int)
        for r in group:
            d = r.get("decision") or ""
            if d:
                decisions.append(d)
            msg = (r.get("mensaje_no_match") or "").strip()
            if msg:
                mensajes.append(msg)
            imp = _safe_load_json(r.get("improvements"), [])
            if isinstance(imp, list):
                improvements_all.extend(x for x in imp if isinstance(x, str))
            ntp = _safe_load_json(r.get("new_training_phrases"), {})
            if isinstance(ntp, dict):
                for intent_key, phrases in ntp.items():
                    if isinstance(phrases, list):
                        new_training_merged.setdefault(intent_key, []).extend(phrases)
                    elif isinstance(phrases, str):
                        new_training_merged.setdefault(intent_key, []).append(phrases)
            it = (r.get("intent_top") or "").strip()
            if it:
                intent_counts[it] += 1
        result[flow] = {
            "cantidad_casos": len(group),
            "decisiones": decisions,
            "resumen_decisiones": _count_values(decisions),
            "mensajes_no_match": list(dict.fromkeys(mensajes))[:50],
            "intent_top_counts": dict(intent_counts),
            "improvements_consolidados": list(dict.fromkeys(improvements_all)),
            "new_training_phrases_consolidados": {k: list(dict.fromkeys(v)) for k, v in new_training_merged.items()},
        }
    return result


def aggregate_by_intent(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Agrupa por intent_top (y flow_ref). Por cada intent: cantidad, decisiones, mensajes, mejoras."""
    by_intent: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        intent = (r.get("intent_top") or "").strip() or "SIN_INTENT"
        flow = (r.get("flow_ref") or "").strip() or "UNKNOWN"
        key = f"{flow}|{intent}"
        by_intent[key].append(r)

    result = {}
    for key, group in sorted(by_intent.items()):
        flow, intent = key.split("|", 1) if "|" in key else ("UNKNOWN", key)
        decisions = [r.get("decision") or "" for r in group if r.get("decision")]
        mensajes = list(dict.fromkeys((r.get("mensaje_no_match") or "").strip() for r in group if (r.get("mensaje_no_match") or "").strip()))[:30]
        improvements_all: List[str] = []
        for r in group:
            imp = _safe_load_json(r.get("improvements"), [])
            if isinstance(imp, list):
                improvements_all.extend(x for x in imp if isinstance(x, str))
        result[key] = {
            "flow": flow,
            "intent": intent,
            "cantidad_casos": len(group),
            "decisiones": decisions,
            "resumen_decisiones": _count_values(decisions),
            "mensajes_no_match_sample": mensajes,
            "improvements_consolidados": list(dict.fromkeys(improvements_all)),
        }
    return result


def _count_values(items: List[str]) -> Dict[str, int]:
    c: Dict[str, int] = defaultdict(int)
    for x in items:
        if x:
            c[x] += 1
    return dict(c)


def build_informe_general(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Construye el payload del informe general: por_flow, por_intent, total_casos."""
    by_flow = aggregate_by_flow(rows)
    by_intent = aggregate_by_intent(rows)
    return {
        "total_casos_no_match": len(rows),
        "por_flow": by_flow,
        "por_intent": by_intent,
    }


def write_informe_general(
    rows: List[Dict[str, Any]],
    path_out_dir: str,
    write_md: bool = True,
) -> None:
    """
    Escribe informe_general_mejora.json y opcionalmente informe_general_mejora.md.
    """
    os.makedirs(path_out_dir, exist_ok=True)
    informe = build_informe_general(rows)

    json_path = os.path.join(path_out_dir, "informe_general_mejora.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)

    if write_md:
        md_path = os.path.join(path_out_dir, "informe_general_mejora.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(_informe_to_md(informe))


def _informe_to_md(informe: Dict[str, Any]) -> str:
    lines = [
        "# Informe general de mejora (NO_MATCH)",
        "",
        f"**Total de casos NO_MATCH:** {informe.get('total_casos_no_match', 0)}",
        "",
        "## Por flow",
        "",
    ]
    for flow, data in (informe.get("por_flow") or {}).items():
        lines.append(f"### {flow}")
        lines.append(f"- Casos: {data.get('cantidad_casos', 0)}")
        res = data.get("resumen_decisiones") or {}
        if res:
            lines.append("- Decisiones: " + ", ".join(f"{k}({v})" for k, v in sorted(res.items(), key=lambda x: -x[1])))
        imps = data.get("improvements_consolidados") or []
        if imps:
            lines.append("- Mejoras sugeridas:")
            for i in imps[:15]:
                lines.append(f"  - {i}")
        ntp = data.get("new_training_phrases_consolidados") or {}
        if ntp:
            lines.append("- Nuevas frases de entrenamiento por intent:")
            for intent, phrases in list(ntp.items())[:10]:
                lines.append(f"  - {intent}: {phrases[:5]}{'...' if len(phrases) > 5 else ''}")
        lines.append("")

    lines.extend(["## Por intent (flow|intent)", ""])
    for key, data in (informe.get("por_intent") or {}).items():
        lines.append(f"- **{key}**: {data.get('cantidad_casos', 0)} casos, decisiones: {data.get('resumen_decisiones', {})}")
    lines.append("")
    return "\n".join(lines)
