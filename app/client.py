import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")

client = (
    OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://github.com/retail-agent",
            "X-Title": "Retail Electronics AI Agent",
        },
    )
    if OPENROUTER_API_KEY
    else None
)


def get_client() -> OpenAI:
    if client is None:
        raise RuntimeError(
            "Configura OPENROUTER_API_KEY en un archivo .env antes de usar el chat."
        )
    return client
