import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL",
    "https://openrouter.ai/api/v1"
)

PLANNER_MODEL = os.getenv(
    "PLANNER_MODEL",
    "nvidia/nemotron-3.5-super-vl:free"
)

VISION_MODEL = os.getenv(
    "VISION_MODEL",
    "nvidia/nemotron-3.5-super-vl:free"
)

LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))


def validate_config():
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY mancante nel file .env")

    if LLM_PROVIDER not in ("openrouter", "openai"):
        raise ValueError("Provider non supportato")
