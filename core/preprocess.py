import pandas as pd
from typing import Dict, List

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

    df['session_id'] = df['session_id'].ffill()
    df['intent_detectado'] = df['intent_detectado'].ffill()
    df['tipo'] = df['tipo'].str.lower()

    return df

def procesar_chats(df: pd.DataFrame) -> Dict[str, List[Dict[str, str]]]:
    sesiones = {}
    for session_id, grupo in df.groupby('session_id'):
        mensajes = []
        for _, fila in grupo.iterrows():
            mensajes.append({
                "texto": str(fila["texto"]),
                "tipo": str(fila["tipo"]),
                "intent_detectado": str(fila["intent_detectado"])
            })
        sesiones[session_id] = mensajes
    return sesiones
