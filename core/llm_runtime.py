"""
LLM Judge embebido (llama-cpp-python). Carga modelo GGUF, judge_case devuelve JSON estricto.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    from llama_cpp import Llama
except (ImportError, FileNotFoundError, OSError):
    Llama = None  # type: ignore

# ---------------------------- Helpers: paths ----------------------------
def _resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(relative).resolve()


def resolve_model_path(model_filename: str) -> Path:
    env = os.environ.get("MODEL_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p
    candidate = Path.cwd() / "models" / model_filename
    if candidate.exists():
        return candidate.resolve()
    bundled = _resource_path(f"models/{model_filename}")
    if bundled.exists():
        return bundled.resolve()
    raise FileNotFoundError(
        f"Model not found. Tried MODEL_PATH, ./models/{model_filename}, and bundled."
    )


# ---------------------------- JSON parsing ----------------------------
_JSON_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


def extract_json_object(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return m.group(0)


def safe_json_loads(text: str) -> Dict[str, Any]:
    return json.loads(extract_json_object(text))


# ---------------------------- Prompt ----------------------------
SYSTEM_JSON_ONLY = (
    "Sos un analista de NLU/Dialogflow. "
    "Respondé SOLO un JSON válido (sin markdown, sin texto extra). "
    "Si falta información, igual devolvé el JSON con decision='AMBIGUOUS' y confidence baja."
)

JSON_SCHEMA_HINT = {
    "decision": "MISSED_EXISTING_INTENT_IN_FLOW | NEW_INTENT_IN_FLOW | MISSING_PARAMETER_HANDLER | FLOW_SWITCH | OUT_OF_SCOPE | AMBIGUOUS",
    "flow_recommended": "string",
    "intent_recommended": ["string"],
    "intents_relevantes": [],
    "why": "string",
    "improvements": [],
    "new_training_phrases": {},
    "suggested_dialogflow": {"parameters": [], "contexts": []},
    "confidence": 0.0,
}


def build_judge_prompt(payload: Dict[str, Any]) -> str:
    return (
        "Tarea: clasificar el NO_MATCH y recomendar acciones en Dialogflow.\n"
        "Reglas:\n"
        "- Elegí UNA decision del enum.\n"
        "- Si el texto del usuario parece ser un VALOR (mes, moneda, adicional, menor, etc.) "
        "dentro de un flow activo, preferí MISSING_PARAMETER_HANDLER.\n"
        "- Si hay un intent existente muy similar (evidence con sim alta), preferí MISSED_EXISTING_INTENT_IN_FLOW.\n"
        "- Si no existe intent y es del dominio del flow, NEW_INTENT_IN_FLOW.\n"
        "- Si es fuera de dominio, OUT_OF_SCOPE.\n\n"
        "Salida: JSON estricto con esta forma (ejemplo de schema, NO inventes campos):\n"
        f"{json.dumps(JSON_SCHEMA_HINT, ensure_ascii=False)}\n\n"
        "INPUT:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


@dataclass
class LLMConfig:
    model_filename: str
    n_ctx: int = 4096
    n_threads: int = 8
    n_batch: int = 256
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 800
    seed: int = 42


class LocalLLM:
    """Single-process LLM runtime using llama.cpp via llama-cpp-python."""

    def __init__(self, cfg: LLMConfig):
        if Llama is None:
            raise ImportError("llama-cpp-python is required. Install with: pip install llama-cpp-python")
        self.cfg = cfg
        model_path = resolve_model_path(cfg.model_filename)
        self.llm = Llama(
            model_path=str(model_path),
            n_ctx=cfg.n_ctx,
            n_threads=cfg.n_threads,
            n_batch=cfg.n_batch,
            seed=cfg.seed,
            verbose=False,
        )

    def chat_json(self, prompt: str) -> Dict[str, Any]:
        out = self.llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_JSON_ONLY},
                {"role": "user", "content": prompt},
            ],
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
            max_tokens=self.cfg.max_tokens,
        )
        text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        try:
            return safe_json_loads(text)
        except Exception:
            repair = (
                "Tu salida no fue JSON válido. Convertí EXACTAMENTE el siguiente contenido a un JSON válido, "
                "sin agregar ni quitar significado. Respondé SOLO JSON:\n" + text
            )
            out2 = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_JSON_ONLY},
                    {"role": "user", "content": repair},
                ],
                temperature=0.0,
                top_p=1.0,
                max_tokens=self.cfg.max_tokens,
            )
            text2 = (out2.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
            return safe_json_loads(text2)

    def judge_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self.chat_json(build_judge_prompt(payload))
        if "confidence" not in result:
            result["confidence"] = 0.5
        return result

    def embed_text(self, text: str) -> List[float]:
        if hasattr(self.llm, "embed"):
            return self.llm.embed(text)
        return []
