"""
Índice TF-IDF sobre training phrases y recuperación de candidatos por intent.
Agregación por intent, score_intent, priorización por flow_ref.
"""
import math
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer


def build_training_index(df_training: pd.DataFrame) -> Dict[str, Any]:
    """
    Construye índice TF-IDF sobre phrase_norm.
    Devuelve dict con: vectorizer, matrix, df (intent, flow, phrase, phrase_norm, row_id).
    """
    texts = df_training["phrase_norm"].fillna("").astype(str).tolist()
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    return {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "df": df_training.reset_index(drop=True),
    }


def retrieve_candidates(
    trigger_user_text_norm: str,
    index: Dict[str, Any],
    flow_ref: str,
    top_intents: int = 10,
    evidence_per_intent: int = 6,
) -> List[Dict[str, Any]]:
    """
    Búsqueda por similitud (coseno), agregación por intent:
    max_sim, avg_sim_top5, hits, score_intent = 0.65*max_sim + 0.25*avg_top5 + 0.10*log(1+hits).
    Priorización: score *= 1.1 si intent.flow == flow_ref (y flow_ref no UNKNOWN/CHIT).
    Devuelve lista de dicts con intent, flow, score, evidence [{phrase, sim}], training_phrases.
    evidence: frases de entrenamiento de ese intent que más se parecieron al trigger (TF-IDF) y su similitud.
    """
    if not trigger_user_text_norm or not index.get("matrix").size:
        return []
    vectorizer = index["vectorizer"]
    matrix = index["matrix"]
    df = index["df"]
    q = vectorizer.transform([trigger_user_text_norm])
    sims = (matrix @ q.T).toarray().ravel()
    df = df.copy()
    df["_sim"] = sims
    by_intent = df.groupby("intent", sort=False)
    results = []
    for intent, grp in by_intent:
        flow = grp["flow"].iloc[0] if "flow" in grp.columns else ""
        top_rows = grp.nlargest(evidence_per_intent + 5, "_sim")
        sim_list = top_rows["_sim"].tolist()
        max_sim = float(max(sim_list)) if sim_list else 0.0
        top5 = sim_list[:5]
        avg_top5 = float(np.mean(top5)) if top5 else 0.0
        hits = len(grp)
        score_intent = 0.65 * max_sim + 0.25 * avg_top5 + 0.10 * math.log(1 + hits)
        if flow_ref and flow_ref not in ("UNKNOWN", "CHIT") and flow == flow_ref:
            score_intent *= 1.1
        evidence = [
            {"phrase": r["phrase"], "sim": float(r["_sim"])}
            for _, r in top_rows.head(evidence_per_intent).iterrows()
        ]
        training_phrases = grp["phrase"].dropna().astype(str).tolist() if "phrase" in grp.columns else []
        results.append({
            "intent": intent,
            "flow": flow,
            "score": round(score_intent, 4),
            "evidence": evidence,
            "training_phrases": training_phrases,
        })
    results.sort(key=lambda x: -x["score"])
    return results[:top_intents]
