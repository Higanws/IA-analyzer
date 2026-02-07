"""
Análisis legacy: por sesión, LLM vía HTTP (Ollama/LM Studio), salida motivo_no_match, intents_relevantes, mejoras, nuevos_ejemplos.
"""
import os
import pandas as pd
import json
import re
from typing import Tuple
from datetime import datetime

from core.preprocess import cargar_chats, procesar_chats
from core.prompt_builder import cargar_intents, cargar_prompt_base, construir_prompt
from core.mistral_runner import MistralRunner
from core.file_manager import guardar_csv


def validar_respuesta_llm(respuesta_llm: dict, intents_validos: list) -> Tuple[bool, str]:
    for campo in ("motivo_no_match", "mejoras", "nuevos_ejemplos", "intents_relevantes"):
        if campo not in respuesta_llm:
            return False, f"Falta campo '{campo}'"

    motivo = respuesta_llm["motivo_no_match"]

    if motivo not in [
        "intent_existente_mal_entrenado",
        "intent_no_existente",
        "mensaje_fuera_de_contexto"
    ]:
        return False, f"motivo_no_match inválido: {motivo}"

    if motivo == "intent_existente_mal_entrenado":
        if not isinstance(respuesta_llm["intents_relevantes"], list) or not respuesta_llm["intents_relevantes"]:
            return False, "Faltan intents_relevantes cuando debería haberlos"
        for intent in respuesta_llm["intents_relevantes"]:
            if intent not in intents_validos:
                return False, f"Intent '{intent}' en intents_relevantes no existe en catálogo"

    ejemplos = respuesta_llm["nuevos_ejemplos"]
    if not isinstance(ejemplos, list):
        return False, "nuevos_ejemplos debe ser lista"
    for ej in ejemplos:
        if not isinstance(ej, str):
            return False, "Algún ejemplo no es string"

    return True, ""


def analizar_chats(path_chat_csv: str, path_intent_csv: str, path_output_csv: str, llm_url: str, llm_id: str, logger_callback=None):
    if logger_callback:
        logger_callback("🚀 Cargando archivos...")

    df_chats = cargar_chats(path_chat_csv)
    sesiones = procesar_chats(df_chats)
    intents_catalogo = cargar_intents(path_intent_csv)
    prompt_base = cargar_prompt_base()

    modelo = MistralRunner(api_url=llm_url, model_name=llm_id)

    resultados = []
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    total = len(sesiones)

    for i, (session_id, mensajes) in enumerate(sesiones.items(), 1):
        if logger_callback:
            logger_callback(f"🧠 Analizando sesión {i}/{total} - ID: {session_id}")

        try:
            prompt, mensaje_no_match = construir_prompt(session_id, mensajes, intents_catalogo, prompt_base)
            respuesta_texto = modelo.enviar_prompt(prompt)

            json_match = re.search(r'\{.*\}', respuesta_texto, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                raise ValueError("La respuesta del modelo no contiene JSON válido.")

            respuesta = json.loads(json_str)
            es_valido, motivo_error = validar_respuesta_llm(respuesta, intents_validos=list(intents_catalogo.keys()))

            if es_valido:
                resultados.append({
                    "fecha": fecha_actual,
                    "session_id": session_id,
                    "mensaje_no_match": mensaje_no_match,
                    "motivo_no_match": respuesta.get("motivo_no_match", ""),
                    "intents_relevantes": ", ".join(respuesta.get("intents_relevantes", [])),
                    "mejoras": respuesta.get("mejoras", ""),
                    "nuevos_ejemplos": " | ".join(respuesta.get("nuevos_ejemplos", []))
                })
            else:
                if logger_callback:
                    logger_callback(f"⚠️ Error de validación en sesión {session_id}: {motivo_error}")

        except Exception as e:
            if logger_callback:
                logger_callback(f"⚠️ Error procesando sesión {session_id}: {str(e)}")
            resultados.append({
                "fecha": fecha_actual,
                "session_id": session_id,
                "mensaje_no_match": "ERROR",
                "motivo_no_match": f"Error procesamiento: {str(e)}",
                "intents_relevantes": "",
                "mejoras": "",
                "nuevos_ejemplos": ""
            })

    guardar_csv(pd.DataFrame(resultados), path_output_csv)

    if logger_callback:
        logger_callback("✅ Análisis finalizado.")
