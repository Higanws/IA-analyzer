# Dialogflow NO_MATCH Analyzer (Local) — Especificación

---

## 0) Nombre del proyecto y objetivo

### Nombre

**Dialogflow NO_MATCH Analyzer (Local)**

### Objetivo

Analizar conversaciones exportadas (CSV de chats) y el dataset de entrenamiento de Dialogflow (CSV de training phrases) para explicar, por cada NO_MATCH:

- Si existía un intent que debía haber matcheado y falló por falta de entrenamiento / variantes.
- Si falta un intent nuevo dentro del flow actual.
- Si el problema no es un intent sino parámetros/entidades/contexto (slot filling) propio de Dialogflow.
- Si hubo cambio de flow o fue out-of-scope.

**Entregable principal:** reporte auditable que sugiera acciones concretas:

- Agregar training phrases a intents existentes
- Crear intent nuevo (y frases sugeridas)
- Crear/ajustar parámetros y entidades (mes, moneda, tipo de tarjeta, menor de edad, etc.)
- Ajustes de contexto (follow-up / contexts)

---

## 1) Restricciones y decisiones clave

### Hardware

- Laptop i7 vPro 1365U, 32GB RAM, iGPU
- LLM debe correr local → preferible 3B–7B cuantizado (GGUF Q4)

### Decisiones

- **NO fine-tuning al inicio:** se logra precisión con retrieval + juez LLM y reglas analíticas.
- El LLM no ve todo el training, solo top-K evidencias (rápido y controlable).
- Se añade clase específica para Dialogflow: **MISSING_PARAMETER_HANDLER**, para evitar falsos “crear intent”.

---

## 2) Arquitectura lógica del sistema

### Visión general (módulos)

1. Ingesta y normalización
2. Indexado de training (embeddings + fallback lexical)
3. Detección de casos NO_MATCH
4. Inferencia de flow + construcción de contexto
5. Retriever de candidatos (top intents + evidencias)
6. Detector analítico de slots (mes/moneda/relación/tipo/etc.)
7. LLM Judge (clasificación + recomendaciones + ejemplos)
8. Post-validación y scoring de confianza
9. Reportes (CSV + JSONL + debug)

### Diagrama (alto nivel)

```
Chats CSV → (parse/normalize) → Cases NO_MATCH
Training CSV → (ffill + normalize) → Index embeddings

Cada case:
  context_builder → retriever → slot_signals → LLM judge → post_rules → report_writer
```

---

## 3) Formatos internos de datos

### 3.1 Chat turn (internal)

| Campo            | Tipo                    |
|------------------|-------------------------|
| `session_id`     | str                     |
| `fecha`          | date                    |
| `tipo`           | `"usuario"` \| `"bot"`  |
| `texto`          | str                     |
| `texto_norm`     | str                     |
| `intent_detectado` | str \| null          |
| `intent_norm`    | str \| null             |
| `is_no_match`    | bool                    |
| `flow_from_intent` | str \| null           |
| `turn_index`     | int (orden dentro de sesión) |

### 3.2 Training row (internal)

Tu training tiene intent “en bloque”; se aplana a:

| Campo        | Tipo   |
|-------------|--------|
| `intent`    | str    |
| `flow`      | str (`intent.split("_")[0]`) |
| `language`  | str    |
| `phrase`    | str    |
| `phrase_norm` | str  |
| `row_id`    | int    |

---

## 4) Reglas de inferencia de Flow (Dialogflow-aware)

### 4.1 Parse de flow desde intent

- Si intent empieza por `NO_MATCH` → flow = `NO_MATCH`
- Si intent empieza por `CHIT_` → flow = `CHIT`
- Si intent contiene `_` → flow = `intent.split("_")[0]`
- Si intent no tiene `_` → flow = intent (fallback)

### 4.2 Flows neutrales

No cortan contexto ni determinan flow_ref por sí mismos:

- CHIT, GENERIC, SALUDO, DERIVACION, AGENTE, etc.
- (Se configuran en un set editable.)

---

## 5) Definición formal de “Caso NO_MATCH” (Case)

Dado que el NO_MATCH está en mensajes del bot:

Un **case** se crea en cada fila donde:

- `tipo="bot"` y `intent_detectado` empieza con `"NO_MATCH"`

**Campos del case:**

- `case_id` = `f"{session_id}:{turn_index}"`
- `no_match_bot_turn` = esa fila
- `trigger_user_turn` = fila inmediatamente anterior con `tipo="usuario"` (si existe)
- `trigger_user_text` = trigger_user_turn.texto
- `trigger_user_text_norm`
- `fecha`
- `session_id`

Si hay NO_MATCH consecutivos, cada uno es un case distinto (ej. s2, s5).

---

## 6) Construcción de contexto (Context Builder)

### 6.1 Definir flow_ref

Regla robusta:

1. Buscar hacia atrás desde `trigger_user_turn` el último turn con `intent_detectado` válido y flow **no neutral** → ese flow es `flow_ref`.
2. Si no hay, buscar último intent válido aunque sea neutral → flow_ref.
3. Si no hay ninguno → `flow_ref="UNKNOWN"`.

Guardar también:

- `last_valid_intent_before_no_match` (no NO_MATCH)

### 6.2 Ventana de contexto

Se construye hacia atrás desde `trigger_user_turn`, incluyendo turnos mientras:

- No superes `MAX_MSG_CONTEXT` (12)
- Y no haya “cambio de flow confirmado”

**Cambio de flow confirmado:** no cortar por un único outlier. Cortar si se detecta:

- 2 intents seguidos con flow != flow_ref y no neutral, o
- 2 de los últimos 3 intents con flow != flow_ref y no neutral

**Inclusión de neutrales:** los turnos con flow neutral se pueden incluir como texto, pero no cuentan como señal de cambio de flow.

### 6.3 Contexto extendido (opcional)

Si `flow_ref_strength` es baja (ej. solo 1 intent del flow antes del NO_MATCH) o hay señales de transición:

- Incluir `prev_flow_context` (máx 3–6 turnos) en un bloque separado.

---

## 7) Retriever de candidatos (Training → intents)

### 7.1 Query

- **Q1** = `trigger_user_text_norm`
- **Q2** opcional = `trigger_user_text_norm + " " + last_user_norm` (si existe y suma)

### 7.2 Búsqueda

- Vector search top **K_UTTERANCES** (50–80)
- (Fallback) TF-IDF top 50 si el texto es muy corto (“Marzo”, “Dólares”)

### 7.3 Agregación por intent

Para cada intent:

- `max_sim`
- `avg_sim_top5`
- `hits`
- `score_intent` = `0.65*max_sim + 0.25*avg_top5 + 0.10*log(1+hits)`

### 7.4 Priorización por flow_ref

Si `flow_ref ∉ {UNKNOWN, CHIT}`:

- `score_intent *= 1.1` si `intent.flow == flow_ref`

No se excluyen flows distintos (para detectar FLOW_SWITCH).

### 7.5 Selección

- **TOP_INTENTS** = 10
- **EVIDENCE_PER_INTENT** = 6
- Evidencias por intent: top frases con su similitud `{phrase, sim}`

---

## 8) Analizador “Slot/Parameter” (Dialogflow entities)

Este módulo es crítico y es **reglas + NER simple** (barato, sin LLM).

### 8.1 Slot signals (diccionario inicial)

| Slot              | Ejemplos / regex |
|-------------------|------------------|
| **Período / Mes (MONTH/PERIOD)** | “enero…diciembre”, “mes pasado”, “este mes”, “mes anterior”, “último mes”, “abril”, “marzo”. Regex: `\b(enero|febrero|...|diciembre)\b`, `mes pasado|mes anterior|último mes|este mes` |
| **Moneda (CURRENCY)** | “dólar(es)”, “usd”, “u$s”, “dolares”. Regex: `\b(usd|u\$s|d[oó]lar(?:es)?)\b` |
| **Tipo de tarjeta (CARD_TYPE)** | “adicional”, “titular”, “suplementaria”. Regex: `\b(adicional|titular|suplementaria)\b` |
| **Relación / Menor de edad (RELATION_MINOR)** | “para mi hijo”, “mi hijo”, “menor”, “menor de edad”, “tutor”. Regex: `\b(hijo|hija|menor|menor de edad|tutor)\b` |
| **“Cuánto” (AMOUNT_QUERY)** | “cuánto”, “hasta cuánto”, “monto”, “máximo”. Regex: `\b(cu[aá]nto|monto|m[aá]ximo|hasta)\b` |

### 8.2 Clasificación preliminar por slots

Se marca como **MISSING_PARAMETER_HANDLER** si:

- `flow_ref` es conocido (no CHIT/UNKNOWN), y
- Hay slot_signals fuertes, y
- El trigger es “valor” o follow-up corto (ej. “Marzo”, “Con dólares”, “Adicional”) o pregunta típica de parámetro (cuánto/monto)

Esto no decide final todavía: se lo pasa como feature al LLM.

---

## 9) LLM Judge (modelo local)

### 9.1 Responsabilidad del LLM

Con contexto + candidates + slot_signals, decide:

**Etiquetas de decisión:**

- MISSED_EXISTING_INTENT_IN_FLOW
- NEW_INTENT_IN_FLOW
- MISSING_PARAMETER_HANDLER
- FLOW_SWITCH
- OUT_OF_SCOPE
- AMBIGUOUS

### 9.2 Prompt (especificación)

El prompt debe:

- Obligar JSON estricto
- Prohibir texto fuera del JSON
- Incluir evidencia (frases) y pedir que cite cuál motivó la decisión

**Entrada al LLM (estructura):**

- flow_ref
- last_valid_intent
- context_messages (lista)
- trigger_user_text
- slot_signals
- candidates (intents con evidencias y sim)

### 9.3 Output JSON (contrato final)

```json
{
  "decision": "MISSED_EXISTING_INTENT_IN_FLOW | NEW_INTENT_IN_FLOW | MISSING_PARAMETER_HANDLER | FLOW_SWITCH | OUT_OF_SCOPE | AMBIGUOUS",
  "flow_recommended": "Prestamos | Cuentas | Tarjetas | Transferencias | UNKNOWN",
  "intent_recommended": ["IntentName"],
  "intents_relevantes": [
    {
      "intent": "IntentName",
      "flow": "FlowName",
      "score": 0.0,
      "evidence": [
        {"phrase": "…", "sim": 0.0}
      ]
    }
  ],
  "why": "explicación corta",
  "improvements": [
    {"intent": "IntentName", "action": "add_training_phrases | create_intent | add_parameters | adjust_context", "detail": "…"}
  ],
  "new_training_phrases": {
    "IntentName": ["...", "..."]
  },
  "suggested_dialogflow": {
    "parameters": [
      {"name": "periodo", "entity": "@sys.date-period|@mes", "examples": ["marzo", "mes pasado"]}
    ],
    "contexts": [
      {"name": "ctx_cuentas_resumen_followup", "lifespan": 2}
    ]
  },
  "confidence": 0.0
}
```

---

## 10) Post-procesado y scoring final

### 10.1 Umbrales de similitud (sin LLM)

- **STRONG_MATCH** >= 0.72
- **WEAK_MATCH** >= 0.55

### 10.2 Reglas de consistencia

- Si STRONG_MATCH existe en algún intent del mismo flow_ref, pero LLM dice NEW_INTENT → bajar confianza y marcar `review_flag`.
- Si slot_signals fuerte + trigger corto (“Marzo”, “Dólares”) y LLM no dijo MISSING_PARAMETER_HANDLER → bajar confianza.
- Si no hay evidencias >0.55 y el texto es claramente no bancario (“torta”) → OUT_OF_SCOPE alto.

### 10.3 Campo review_flag

`review_flag` = true si hay contradicción fuerte entre retrieval y decisión.

---

## 11) Outputs del sistema

### 11.1 CSV final (1 fila por case)

Columnas recomendadas:

- fecha, session_id, case_id
- mensaje_no_match (trigger_user_text)
- bot_no_match_text
- flow_ref, last_valid_intent
- decision, flow_recommended, intent_top
- intents_relevantes (string JSON corto)
- top_evidence (3 frases)
- slot_signals
- improvements
- new_training_phrases (JSON string)
- suggested_dialogflow (JSON string)
- confidence, review_flag

### 11.2 JSONL (auditoría)

Un JSON por case con: contexto completo, top utterances raw con sim, prompt LLM, respuesta LLM, post_rules aplicadas.

### 11.3 Carpeta debug opcional

`/outputs/cases_debug/{case_id}.json`

---

## 12) Resultado esperado en tus sesiones (con tu training)

### s1 case — “Cuánto me pueden dar?”

- flow_ref = Prestamos (último intent válido no neutral: Prestamos_Solicitud)
- slot_signals: AMOUNT_QUERY (cuánto/monto)
- candidates: Prestamos_Solicitud probablemente no tiene frases de “cuánto”, sim media/baja.
- **Decisión esperada:** NEW_INTENT_IN_FLOW (Prestamos)
- **Intent sugerido:** Prestamos_MontoMaximo o Prestamos_SimulacionMonto
- **Training phrases nuevas:** “¿Cuánto me pueden dar?”, “¿Hasta cuánto me prestan?”, “¿Cuál es el monto máximo del préstamo?”, “¿De cuánto puede ser el préstamo?”
- Dialogflow sugerido: parameter opcional `monto_deseado` si aplica.

### s2 cases — “El del mes pasado” y “Marzo”

- flow_ref = Cuentas
- slot_signals: MONTH/PERIOD fuerte
- candidatos: Cuentas_Resumen sim media; training no captura período.
- **Decisión esperada:** MISSING_PARAMETER_HANDLER
- Sugerencias Dialogflow: agregar parámetro `periodo` con entity @sys.date-period o @mes; follow-up context `ctx_cuentas_resumen` lifespan 2–5; training: “del mes pasado”, “el de marzo”, “abril”, “este mes”.

### s3 case — “Pero es tarjeta adicional”

- flow_ref = Tarjetas
- slot_signals: CARD_TYPE fuerte
- Tarjetas_Resumen existe pero no capta “adicional”.
- **Decisión esperada:** MISSING_PARAMETER_HANDLER (preferible). Parameter `tipo_tarjeta` entity @tipo_tarjeta {titular, adicional}; training: “tarjeta adicional”, “es adicional”, “no la titular, la adicional”. Si no usan params: NEW_INTENT_IN_FLOW Tarjetas_Resumen_Adicional.

### s4 case — “Con dólares”

- flow_ref = Transferencias
- slot_signals: CURRENCY fuerte
- **Decisión esperada:** MISSING_PARAMETER_HANDLER o NEW_INTENT_IN_FLOW si es caso especial. Parameter `moneda` entity @currency o custom {ARS, USD}; training: “en dólares”, “con usd”, “desde cuenta en dólares”.

### s5 cases — “Para mi hijo” y “Es menor de edad”

- flow_ref = Cuentas
- slot_signals: RELATION_MINOR fuerte
- **Decisión esperada:** NEW_INTENT_IN_FLOW (Cuentas). Intent sugerido: Cuentas_Alta_Menor / Cuentas_Alta_CuentaMenor. Training: “Quiero abrir una cuenta para mi hijo”, “Cuenta para menor de edad”, “Mi hijo es menor, ¿puede abrir cuenta?”. Parameter `es_menor` + entidad boolean o intent dedicado + contexto.

---

## 13) Arquitectura técnica (implementación)

### 13.1 Ejecución local

```bash
python analyzer.py --chats data/chats.csv --training data/training.csv --out outputs/
```

### 13.2 Componentes (clases/funciones)

- `load_chats()`, `load_training_ffill()`
- `normalize_text()`
- `build_training_index()`
- `extract_no_match_cases()`
- `infer_flow_ref()`
- `build_context_window()`
- `retrieve_candidates()`
- `detect_slot_signals()`
- `judge_with_llm()` (ollama/llama.cpp/LM Studio)
- `post_validate()`
- `write_reports()`

### 13.3 LLM runtime

- Ollama o LM Studio como servidor local HTTP
- Modelo: Qwen2.5 3B Instruct Q4 (rápido)
- Si querés más criterio: Qwen2.5 7B Q4 (más lento)

---

## 14) Plan de calidad y métricas

### 14.1 Métricas internas

- % NO_MATCH clasificados como: missed_existing, new_intent, missing_parameter, out_of_scope
- Distribución por flow
- Top intents sugeridos más frecuentes
- review_flag rate (contradicciones)

### 14.2 Validación manual rápida

Muestreo de 50 cases: precisión en decisión, utilidad de ejemplos propuestos, utilidad de sugerencias de parameters/contexts.

---

## 15) Roadmap (fases)

1. **Fase 1:** pipeline sin LLM (retrieval + slots + heurística de decisión)
2. **Fase 2:** integrar LLM judge (mejora cualitativa + generación de ejemplos)
3. **Fase 3:** guardar dataset de casos y, si hace falta, LoRA (3080) solo para mejorar consistencia del JSON/criterio
4. **Fase 4:** UI (customtkinter) y export para re-entrenar/pegar en Dialogflow

---

# Parte II: LLM embebido (llama.cpp)

Cómo se levantará el modelo: detalle técnico completo del módulo **Opción 1: llama.cpp embebido con llama-cpp-python**: inicialización del modelo dentro del exe, ejecución del judge con JSON estricto, embeddings (opcional), paths en PyInstaller y robustez del parseo.

---

## 1) Responsabilidad del módulo

**`llm_runtime.py`**

- Carga un modelo .gguf en el mismo proceso (sin Ollama).
- Expone 2 funciones principales:
  - `judge_case(payload)` → dict (LLM “juez” que devuelve JSON estricto)
  - `embed_text(text)` → list[float] (opcional para retrieval)
- Incluye: control de threads/context, límites de tokens, reintentos de parseo JSON sin inventar contenido, resolución de ruta del modelo en desarrollo y en exe empaquetado.

---

## 2) Dependencias

- **llama-cpp-python** (bindings a llama.cpp)
- stdlib: json, re, os, sys, pathlib, dataclasses, typing

Nota: en Windows, llama-cpp-python trae binarios o compila. Para un exe estable, conviene fijar versión y testear en una VM limpia.

---

## 3) Configuración recomendada (para tu laptop)

- Modelo: Qwen2.5 3B Instruct GGUF Q4 (o Llama 3.2 3B Q4)
- n_ctx=4096
- n_threads=6..10 (i7 1365U: 8)
- n_batch=128..512 (256 default CPU)
- temperature=0.2
- max_tokens=600..900

---

## 4) Implementación lista para usar

**Archivo:** `src/llm_runtime.py`

```python
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List

from llama_cpp import Llama


# ----------------------------
# Helpers: paths (dev vs exe)
# ----------------------------
def _resource_path(relative: str) -> Path:
    """
    Returns absolute path to a resource. Works in:
    - development: relative to project root (or cwd)
    - PyInstaller: relative to sys._MEIPASS (extracted temp folder)
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")) / relative
    return Path(relative).resolve()


def resolve_model_path(model_filename: str) -> Path:
    """
    Strategy:
    1) If env var MODEL_PATH exists, use it.
    2) Look for ./models/<file> relative to cwd (best for onedir exe).
    3) Look for bundled resource path (PyInstaller add-data).
    """
    env = os.environ.get("MODEL_PATH")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p

    # For onedir distribution: exe in root, models folder next to it
    candidate = Path.cwd() / "models" / model_filename
    if candidate.exists():
        return candidate.resolve()

    # For PyInstaller add-data
    bundled = _resource_path(f"models/{model_filename}")
    if bundled.exists():
        return bundled.resolve()

    raise FileNotFoundError(
        f"Model not found. Tried env MODEL_PATH, ./models/{model_filename}, and bundled resource."
    )


# ----------------------------
# JSON parsing robustness
# ----------------------------
_JSON_RE = re.compile(r"\{.*\}", flags=re.DOTALL)


def extract_json_object(text: str) -> str:
    """Extract the first JSON object from a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in model output.")
    return m.group(0)


def safe_json_loads(text: str) -> Dict[str, Any]:
    obj_str = extract_json_object(text)
    return json.loads(obj_str)


# ----------------------------
# Prompt contract
# ----------------------------
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
        text = out["choices"][0]["message"]["content"].strip()
        try:
            return safe_json_loads(text)
        except Exception:
            repair_prompt = (
                "Tu salida no fue JSON válido.\n"
                "Convertí EXACTAMENTE el siguiente contenido a un JSON válido, "
                "sin agregar ni quitar significado. Respondé SOLO JSON:\n"
                f"{text}"
            )
            out2 = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": SYSTEM_JSON_ONLY},
                    {"role": "user", "content": repair_prompt},
                ],
                temperature=0.0,
                top_p=1.0,
                max_tokens=self.cfg.max_tokens,
            )
            text2 = out2["choices"][0]["message"]["content"].strip()
            return safe_json_loads(text2)

    def judge_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prompt = build_judge_prompt(payload)
        return self.chat_json(prompt)

    def embed_text(self, text: str) -> List[float]:
        return self.llm.embed(text)
```

---

## 5) Payload para judge_case

Estructura mínima recomendada:

```json
{
  "session_id": "s1",
  "case_id": "s1:6",
  "flow_ref": "Prestamos",
  "last_valid_intent": "Prestamos_Solicitud",
  "context_messages": [
    {"tipo": "usuario", "texto": "Quiero solicitar un préstamo", "intent": null},
    {"tipo": "bot", "texto": "Tenemos varias opciones...", "intent": "Prestamos_Solicitud"},
    {"tipo": "usuario", "texto": "Cuánto me pueden dar?", "intent": null}
  ],
  "trigger_user_text": "Cuánto me pueden dar?",
  "slot_signals": ["AMOUNT_QUERY"],
  "candidates": [
    {"intent": "Prestamos_Solicitud", "flow": "Prestamos", "score": 0.58, "evidence": [{"phrase": "Quiero solicitar un préstamo", "sim": 0.61}]}
  ]
}
```

---

## 6) Estabilidad en EXE

- **Singleton:** cargar el modelo solo una vez (LocalLLM una instancia global).
- **Paths:** recomendado `--onedir` y el .gguf en `models/` al lado del exe. `resolve_model_path()` ya contempla MODEL_PATH, ./models/, y recurso bundled.
- **JSON:** system prompt “solo JSON”, `extract_json_object`, repair loop con temperature=0.

---

## 7) Integración en analyzer

```python
from llm_runtime import LocalLLM, LLMConfig

llm = LocalLLM(LLMConfig(model_filename="qwen2.5-3b-instruct-q4.gguf"))
# dentro del loop de cases
result = llm.judge_case(payload)
```

---

## 8) Parámetros sugeridos

- n_ctx=4096, n_threads=8, n_batch=256, temperature=0.2, max_tokens=800

---

## Consideraciones finales

- Implementar **test de función** para el módulo LLM y el pipeline de casos.

---

# Análisis a profundidad de los cambios

Este apartado resume las diferencias entre la especificación anterior y el **repositorio actual** (monolito con API HTTP y salida simple).

## Cambios conceptuales

| Aspecto | Repo actual | Especificación (modificacione) |
|--------|--------------|---------------------------------|
| **Objetivo** | Detectar y clasificar NO_MATCH con un LLM vía API | Mismo objetivo + reporte auditable con acciones concretas (training phrases, intents nuevos, parámetros/contextos Dialogflow). |
| **LLM** | MistralRunner → HTTP (Ollama/LM Studio) | Opción embebida: llama-cpp-python, modelo GGUF en proceso, sin servidor externo. |
| **Entrada** | Chat.csv + Intent.csv; sesiones agrupadas. | Chats + Training CSV con **flatten** por frase; turnos con `texto_norm`, `flow_from_intent`, `turn_index`. |
| **Definición de caso** | Por sesión / mensaje según lógica actual. | **Case** = cada fila donde tipo=bot e intent empieza con NO_MATCH; case_id = session_id:turn_index. |
| **Contexto** | Historial de sesión para el prompt. | **flow_ref** (inferido hacia atrás), ventana de contexto con reglas de “cambio de flow” y flows neutrales; MAX_MSG_CONTEXT=12. |
| **Similitud** | No hay retrieval. | **Retriever:** embeddings (o TF-IDF fallback), agregación por intent, score_intent, priorización por flow_ref, TOP_INTENTS=10, EVIDENCE_PER_INTENT=6. |
| **Slots/parámetros** | No existe. | **Slot signals:** MONTH/PERIOD, CURRENCY, CARD_TYPE, RELATION_MINOR, AMOUNT_QUERY con regex; clasificación preliminar MISSING_PARAMETER_HANDLER. |
| **Decisión LLM** | motivo_no_match: intent_existente_mal_entrenado \| intent_no_existente \| mensaje_fuera_de_contexto. | **decision:** MISSED_EXISTING_INTENT_IN_FLOW, NEW_INTENT_IN_FLOW, MISSING_PARAMETER_HANDLER, FLOW_SWITCH, OUT_OF_SCOPE, AMBIGUOUS. |
| **Salida LLM** | motivo_no_match, intents_relevantes, mejoras, nuevos_ejemplos. | JSON ampliado: decision, flow_recommended, intent_recommended, intents_relevantes (con evidence), why, improvements, new_training_phrases, suggested_dialogflow (parameters + contexts), confidence. |
| **Post-proceso** | Validación de campos y valores. | Umbrales STRONG_MATCH/WEAK_MATCH, reglas de consistencia retrieval vs LLM, **review_flag**. |
| **Reportes** | analisis_no_match.csv. | CSV detallado (más columnas) + JSONL auditoría + opcional cases_debug por case_id. |

## Cambios técnicos

- **Preproceso:** de “cargar chats + agrupar por sesión” a “normalizar turnos, inferir flow por intent, detectar is_no_match, construir cases”.
- **Training:** de “cargar intents” a “load_training_ffill + normalizar frases + build_training_index” (embeddings + fallback lexical).
- **Nuevos módulos:** context_builder, retriever, slot_signals, llm_runtime (LocalLLM), post_validate, report_writer (CSV + JSONL + debug).
- **Config:** de URL + model_id a ruta de modelo GGUF + n_ctx, n_threads, n_batch, etc., y opción de MODEL_PATH para exe.
- **Ejecución:** de “app GUI + analyzer interno” a CLI `analyzer.py --chats --training --out` como base, con roadmap hacia UI (Fase 4).

## Riesgos y dependencias

- **llama-cpp-python:** binarios/compilación en Windows; fijar versión y probar en entorno limpio.
- **Tamaño del modelo:** GGUF 3B Q4 en disco y en RAM; singleton y una sola carga por ejecución.
- **Compatibilidad con GUI actual:** las vistas (analysis_view, config_view, etc.) asumen el flujo y CSV actuales; habrá que adaptar o duplicar flujo “nuevo pipeline” vs “legacy”.

---

# Plan para editar el repo actual

Objetivo: alinear el repositorio **IA-analyzer** con la especificación de **Dialogflow NO_MATCH Analyzer (Local)** de forma incremental, sin romper la ejecución actual hasta que el nuevo pipeline esté listo.

## Fase 0: Preparación (sin tocar flujo actual)

| Paso | Acción |
|------|--------|
| 0.1 | Crear carpeta `core/spec/` o `core/config/` y mover allí constantes compartidas: MAX_MSG_CONTEXT=12, TOP_INTENTS=10, EVIDENCE_PER_INTENT=6, STRONG_MATCH=0.72, WEAK_MATCH=0.55, set de flows neutrales (CHIT, GENERIC, SALUDO, etc.). |
| 0.2 | Documentar en `DOCUMENTACION.md` la existencia de dos modos: “actual (API)” y “nuevo (embebido + retrieval)” cuando existan. |
| 0.3 | Dependencias en `requirements.txt` (consolidado); `llama-cpp-python` lo instala el script `entorno/install_llm.py` (en Windows con wheel CPU si aplica). |

## Fase 1: Datos y casos NO_MATCH

| Paso | Acción |
|------|--------|
| 1.1 | En `core/preprocess.py`: extender `cargar_chats()` para devolver DataFrame con columnas alineadas al “Chat turn (internal)”: session_id, fecha, tipo, texto, texto_norm (normalize_text), intent_detectado, intent_norm, is_no_match, flow_from_intent, turn_index. Mantener compatibilidad con `procesar_chats()` si lo usan las vistas. |
| 1.2 | Implementar `load_training_ffill()` y normalización de frases: leer CSV de intents/training, aplanar a una fila por (intent, phrase), con intent, flow (parse por “_”), language, phrase, phrase_norm, row_id. |
| 1.3 | Nuevo módulo `core/cases.py`: `extract_no_match_cases(df_turns)` que recorra filas con tipo=bot e intent_detectado empezando por NO_MATCH, y por cada una construya el case (case_id, no_match_bot_turn, trigger_user_turn, trigger_user_text, trigger_user_text_norm, fecha, session_id). |
| 1.4 | Tests unitarios: al menos un test que, dado un Chat.csv pequeño con un NO_MATCH, verifique que se genera un case con trigger_user_text correcto. |

## Fase 2: Contexto y flow

| Paso | Acción |
|------|--------|
| 2.1 | En `core/` (o `core/context_builder.py`): implementar `infer_flow_ref(trigger_user_turn, df_turns)` según la regla “último intent válido no neutral hacia atrás”, y `build_context_window(trigger_user_turn, df_turns, flow_ref, max_msgs, neutral_flows)` con regla de “cambio de flow confirmado”. |
| 2.2 | Integrar en el flujo de cases: para cada case, calcular flow_ref y context_messages antes de llamar al retriever. |

## Fase 3: Retriever

| Paso | Acción |
|------|--------|
| 3.1 | Definir interfaz del índice: “indexar” lista de (phrase_norm, intent, flow, row_id) con embeddings (o solo TF-IDF al inicio). Carpeta `core/retriever.py` o `core/index.py`. |
| 3.2 | Implementar `retrieve_candidates(trigger_user_text_norm, index, flow_ref, top_intents=10, evidence_per_intent=6)` con agregación por intent (max_sim, avg_sim_top5, hits, score_intent) y priorización por flow_ref. |
| 3.3 | Si se usa embeddings: añadir en `llm_runtime` (o módulo aparte) la generación de vectores; si no, usar solo TF-IDF para Fase 1 del roadmap. |

## Fase 4: Slot signals

| Paso | Acción |
|------|--------|
| 4.1 | Nuevo módulo `core/slot_signals.py`: diccionario de slots (MONTH/PERIOD, CURRENCY, CARD_TYPE, RELATION_MINOR, AMOUNT_QUERY) con regex según la especificación. Función `detect_slot_signals(trigger_user_text_norm)` que devuelva lista de señales detectadas. |
| 4.2 | (Opcional) Clasificación preliminar “MISSING_PARAMETER_HANDLER” según flow_ref conocido + slot_signals fuertes + trigger corto; exponer como feature para el LLM, sin forzar aún la decisión final. |

## Fase 5: LLM Judge embebido

| Paso | Acción |
|------|--------|
| 5.1 | Crear `core/llm_runtime.py` (o `src/llm_runtime.py` según especificación) con: `_resource_path`, `resolve_model_path`, `extract_json_object`, `safe_json_loads`, SYSTEM_JSON_ONLY, build_judge_prompt, LLMConfig, LocalLLM (judge_case, chat_json, opcional embed_text). |
| 5.2 | Configuración: leer model path (o MODEL_PATH) desde config o CLI; usar LLMConfig con n_ctx=4096, n_threads=8, n_batch=256, temperature=0.2, max_tokens=800. |
| 5.3 | Construir payload por case: flow_ref, last_valid_intent, context_messages, trigger_user_text, slot_signals, candidates (con evidence). Llamar `llm.judge_case(payload)` y parsear JSON. |
| 5.4 | Adaptar validación: en lugar de motivo_no_match + intents_relevantes antiguos, validar campos del nuevo contrato (decision, flow_recommended, improvements, new_training_phrases, suggested_dialogflow, confidence). |

## Fase 6: Post-validación y reportes

| Paso | Acción |
|------|--------|
| 6.1 | `core/post_validate.py`: aplicar umbrales STRONG_MATCH/WEAK_MATCH, reglas de consistencia (STRONG_MATCH en flow_ref + NEW_INTENT → bajar confianza y review_flag; slot_signals fuerte sin MISSING_PARAMETER_HANDLER → bajar confianza; sin evidencias y texto no bancario → OUT_OF_SCOPE). |
| 6.2 | `core/report_writer.py` (o extender file_manager): escribir CSV con columnas del §11.1; opcional JSONL con contexto, utterances, prompt, respuesta, post_rules; opcional carpeta cases_debug con un JSON por case_id. |
| 6.3 | Salida: directorio `outputs/` por defecto (o --out); nombres fijos o configurables para analisis_no_match.csv y auditoría.jsonl. |

## Fase 7: Orquestador y CLI

| Paso | Acción |
|------|--------|
| 7.1 | Nuevo script `analyzer.py` en la raíz (o renombrar/refactorizar el actual): flujo “nuevo pipeline” = load_chats → normalizar → load_training_ffill → build_training_index → extract_no_match_cases → por cada case: infer_flow_ref, build_context_window, retrieve_candidates, detect_slot_signals, judge_with_llm, post_validate → write_reports. |
| 7.2 | Argumentos CLI: --chats, --training, --out; opcional --config para JSON con paths y parámetros del modelo. |
| 7.3 | Mantener `core/analyzer.py` actual (o renombrarlo a `analyzer_legacy.py`) para que la GUI siga usando el flujo API si se desea; en la GUI, añadir opción “Pipeline nuevo (local)” que llame al nuevo orquestador y muestre el CSV/JSONL resultante. |

## Fase 8: Calidad y entregables

| Paso | Acción |
|------|--------|
| 8.1 | Implementar test de función para: (a) extracción de cases a partir de un CSV de chat con NO_MATCH; (b) infer_flow_ref y build_context_window con un mini DataFrame; (c) slot_signals con frases tipo “Marzo”, “dólares”, “para mi hijo”; (d) parseo del JSON del judge (mock o modelo pequeño). |
| 8.2 | Actualizar `DOCUMENTACION.md` con la nueva arquitectura, formatos de CSV/JSONL y uso del analyzer.py (CLI) y de la GUI con pipeline nuevo. |
| 8.3 | Si se empaqueta con PyInstaller: --onedir, modelo en `models/` junto al exe, documentar MODEL_PATH; probar resolve_model_path en entorno empaquetado. |

## Orden sugerido de edición

1. **Fase 0** → **Fase 1** (datos y casos): base para todo lo demás.  
2. **Fase 2** (contexto/flow) → **Fase 3** (retriever, aunque sea solo TF-IDF).  
3. **Fase 4** (slots) en paralelo o justo antes del LLM.  
4. **Fase 5** (llm_runtime + integración judge).  
5. **Fase 6** (post_validate + reportes) → **Fase 7** (orquestador + CLI).  
6. **Fase 8** (tests y documentación) a lo largo; cerrar con tests de función y actualización de DOCUMENTACION.md.

Con esto el repo queda alineado con la especificación y con un plan claro para editar el código actual paso a paso.
