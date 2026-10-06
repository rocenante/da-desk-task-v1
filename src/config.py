## src/config.py
"""Application configuration values shared across the tariff RAG pipeline."""

import os

# Project root and derived paths are configured once here so the rest of the app
# can stay portable across local development environments.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARIFF_DATA_PATH = os.path.join(BASE_DIR, "data", "Port Tariff vertical.pdf")
VESSEL_DATA_PATH = os.path.join(BASE_DIR, "data", "vessel.json")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_tariff_db")

LM_STUDIO_MODEL = "meta-llama-3.1-8b-instruct" # "google/gemma-4-12b"
# Kept for the archived main_1.py entry point.
OLLAMA_MODEL = "gemma4:12b"
BASE_URL = "http://127.0.0.1:1234/v1"
API_KEY = "lm-studio"
TEMPERATURE = 0.1

EMBEDDING_MODEL_NAME = "qwen3-embedding:latest"     # "nomic-embed-text"  # "mxbai-embed-large"  #