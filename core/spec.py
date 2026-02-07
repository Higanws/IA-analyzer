"""
Constantes compartidas para el pipeline Dialogflow NO_MATCH Analyzer.
Referencia: Modif/modificacione.md
"""
import os

# Contexto y ventana
MAX_MSG_CONTEXT = 12

# Retriever
TOP_INTENTS = 10
EVIDENCE_PER_INTENT = 6

# Post-validación
STRONG_MATCH = 0.72
WEAK_MATCH = 0.55

# Flows que no cortan contexto ni determinan flow_ref por sí mismos
FLOWS_NEUTRALES = frozenset({
    "CHIT", "GENERIC", "SALUDO", "DERIVACION", "AGENTE", "NO_MATCH"
})

# Paralelismo (ThreadPoolExecutor)
MAX_WORKERS = min(max((os.cpu_count() or 4) - 1, 1), 8)
