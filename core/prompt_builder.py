import unicodedata
import pandas as pd
from typing import List, Dict

PROMPT_BASE = """
Eres un experto analista de conversaciones de chatbot.

Tu tarea es:
- Analizar el historial completo de la conversación.
- Determinar por qué el último mensaje del usuario no fue correctamente entendido por el bot (NO_MATCH).
- Elegir una de estas causas como `motivo_no_match`:

  1. "intent_existente_mal_entrenado"
  2. "intent_no_existente"
  3. "mensaje_fuera_de_contexto"

También podés:
- Sugerir mejoras al intent detectado si está mal entrenado.
- Sugerir hasta 2 nuevos ejemplos si el intent no existe.

🛈 Ten en cuenta: el intent detectado en el mensaje del usuario se refleja en la respuesta del bot que le sigue. El NO_MATCH se registra en la respuesta del bot, pero lo que no fue entendido fue el mensaje previo del usuario.

Instrucciones:
- Basate exclusivamente en el historial de conversación y los intents disponibles.
- No supongas intenciones no expresadas.
- Responde únicamente en formato JSON válido.
- Sé conciso y directo. No agregues texto explicativo.

Datos disponibles:

Session ID: {session_id}

Historial de conversación:  
{historial_chat}

Mensaje que no matcheó:  
{mensaje_no_match}

Catálogo de intents (nombre y 4 ejemplos por intent):  
{intents_catalogo}

Formato obligatorio:

{{
  "motivo_no_match": "",               
  "intents_relevantes": [],            
  "mejoras": "",                       
  "nuevos_ejemplos": []                
}}
"""

def normalizar(texto):
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8').lower()

def cargar_intents(path_intent_csv: str) -> Dict[str, List[str]]:
    df = pd.read_csv(path_intent_csv)
    df['Intent Display Name'] = df['Intent Display Name'].ffill()

    intents = {}
    for intent_name, grupo in df.groupby('Intent Display Name'):
        frases = grupo['Phrase'].dropna().tolist()
        frases_limpias = list(set([f.strip() for f in frases if len(f.strip()) > 5]))
        if len(frases_limpias) >= 2:
            intents[intent_name] = frases_limpias

    return intents

def cargar_prompt_base():
    return PROMPT_BASE

def construir_prompt(session_id, mensajes, intents_catalogo, prompt_base):
    mensaje_no_match = ""
    for i in reversed(range(len(mensajes))):
        if mensajes[i]["tipo"] == "usuario":
            mensaje_no_match = mensajes[i]["texto"]
            break

    historial = ""
    for m in mensajes:
        historial += f"{m['tipo']}: {m['texto']} (intent_detectado: {m['intent_detectado']})\n"

    intents_catalogo_txt = ""
    for intent, frases in intents_catalogo.items():
        frases_mostradas = frases[:4]
        frases_fmt = "\n".join([f"- {f}" for f in frases_mostradas])
        intents_catalogo_txt += f"Intent: {intent}\nEjemplos:\n{frases_fmt}\n\n"

    prompt_final = prompt_base.format(
        session_id=session_id,
        historial_chat=historial.strip(),
        mensaje_no_match=mensaje_no_match,
        intents_catalogo=intents_catalogo_txt.strip()
    )

    return prompt_final, mensaje_no_match
