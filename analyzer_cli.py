#!/usr/bin/env python3
"""
CLI para el pipeline nuevo de análisis NO_MATCH.
Uso: python analyzer_cli.py --chats data/Chat.csv --training data/Intent.csv --out outputs/
"""
import argparse
import os
from core.config_loader import load_config, get_config_path, get_model_filename_from_config
from core.analyzer import analizar_pipeline


def main():
    p = argparse.ArgumentParser(description="Dialogflow NO_MATCH Analyzer (pipeline nuevo)")
    p.add_argument("--chats", required=True, help="Ruta al CSV de chats")
    p.add_argument("--training", required=True, help="Ruta al CSV de training/intents")
    p.add_argument("--out", default="outputs", help="Directorio de salida (default: outputs/)")
    p.add_argument("--config", help="Ruta a config JSON (opcional; model_path para LLM)")
    p.add_argument("--no-llm", action="store_true", help="No llamar al LLM (solo contexto + retriever + slots)")
    args = p.parse_args()
    config = {}
    config_path = args.config if args.config and os.path.isfile(args.config) else get_config_path()
    if os.path.isfile(config_path):
        config = load_config(config_path).copy()
        config.pop("csv_chats", None)
        config.pop("csv_intents", None)
        config.pop("output_folder", None)
    model_filename = get_model_filename_from_config(config) if config else ""
    if args.no_llm:
        model_filename = ""
    config["model_filename"] = model_filename or None
    analizar_pipeline(
        path_chat_csv=args.chats,
        path_training_csv=args.training,
        path_out=args.out,
        config=config,
        logger_callback=print,
        use_llm=bool(model_filename),
    )


if __name__ == "__main__":
    main()
