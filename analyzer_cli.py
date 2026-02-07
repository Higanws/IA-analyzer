#!/usr/bin/env python3
"""
CLI para el pipeline nuevo de análisis NO_MATCH.
Uso: python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/
"""
import argparse
import json
import os
from core.analyzer import analizar_pipeline


def main():
    p = argparse.ArgumentParser(description="Dialogflow NO_MATCH Analyzer (pipeline nuevo)")
    p.add_argument("--chats", required=True, help="Ruta al CSV de chats")
    p.add_argument("--training", required=True, help="Ruta al CSV de training/intents")
    p.add_argument("--out", default="outputs", help="Directorio de salida (default: outputs/)")
    p.add_argument("--config", help="Ruta a config JSON (opcional; si tiene model_filename se usará LLM)")
    p.add_argument("--no-llm", action="store_true", help="No llamar al LLM (solo contexto + retriever + slots)")
    args = p.parse_args()
    config = {}
    if args.config and os.path.isfile(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "csv_chats" in config:
            config.pop("csv_chats", None)
        if "csv_intents" in config:
            config.pop("csv_intents", None)
        if "output_folder" in config:
            config.pop("output_folder", None)
        model_path = config.get("model_path") or config.get("model_filename")
        if model_path:
            config["model_filename"] = model_path
    if args.no_llm:
        config["model_filename"] = None
    analizar_pipeline(
        path_chat_csv=args.chats,
        path_training_csv=args.training,
        path_out=args.out,
        config=config,
        logger_callback=print,
        use_llm=not args.no_llm and bool(config.get("model_filename")),
    )


if __name__ == "__main__":
    main()
