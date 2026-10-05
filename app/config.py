"""Settings from the environment (.env). Every model and feature is switchable here, so the judged build is one config."""
import os
import pathlib

try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover
    pass


def env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def flag(name, default=True):
    return str(env(name, "1" if default else "0")).lower() in ("1", "true", "yes", "on")


# provider: azure (product) | github (free test) | ollama (local, offline fallback)
LLM_PROVIDER = env("LLM_PROVIDER", "ollama")
AZURE_OPENAI_ENDPOINT = (env("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
AZURE_OPENAI_API_KEY = env("AZURE_OPENAI_API_KEY")
GITHUB_MODELS_TOKEN = env("GITHUB_MODELS_TOKEN")
OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", "gemma4:e4b-it-qat")

MODEL_ANSWER = env("MODEL_ANSWER", "gpt-5.4")
MODEL_JUDGE = env("MODEL_JUDGE", "gpt-5.4-mini")
MODEL_ANSWER_FALLBACK = env("MODEL_ANSWER_FALLBACK", "")  # second deployment if the first fails
EFFORT_ANSWER = env("EFFORT_ANSWER", "low")
EFFORT_JUDGE = env("EFFORT_JUDGE", "low")

EMBED_PROVIDER = env("EMBED_PROVIDER", "ollama")  # azure | ollama | none
MODEL_EMBED = env("MODEL_EMBED", "text-embedding-3-large")
EMBED_DIM = int(env("EMBED_DIM", "1024"))
OLLAMA_EMBED_MODEL = env("OLLAMA_EMBED_MODEL", "bge-m3")

SPEECH_KEY = env("SPEECH_KEY")
SPEECH_REGION = env("SPEECH_REGION")

FEATURES = {k: flag("FEATURE_" + k.upper(), True) for k in
            ("audio", "study_tools", "recite", "word", "takhrij", "srs", "notebook")}
DAILY_QUESTION_CAP = int(env("DAILY_QUESTION_CAP", "300"))
PER_IP_PER_MINUTE = int(env("PER_IP_PER_MINUTE", "6"))

# USD per 1M tokens (input, output). Reasoning tokens bill as output. Unknown models report tokens only.
PRICES = {
    "gpt-5": (1.25, 10.0), "gpt-5-mini": (0.25, 2.0), "gpt-5-nano": (0.05, 0.40),
    "openai/gpt-5": (1.25, 10.0), "openai/gpt-5-mini": (0.25, 2.0),
    "text-embedding-3-large": (0.13, 0.0), "text-embedding-3-small": (0.02, 0.0),
}
for _k in ("ANSWER", "JUDGE"):  # prices for newer deployments can be set in .env: PRICE_ANSWER=in,out
    if env("PRICE_" + _k):
        _i, _o = (float(x) for x in env("PRICE_" + _k).split(","))
        PRICES[env("MODEL_" + _k, "")] = (_i, _o)
