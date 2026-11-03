"""OpenAI-SDK client pointed at the Meta API."""
import os

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_BASE_URL = "https://api.meta.ai/v1"


class MissingApiKeyError(RuntimeError):
    """The server has no API key: a deployment problem, not a student mistake."""


def get_client() -> OpenAI:
    load_dotenv()
    api_key = os.environ.get("MUSE_API_KEY")
    if not api_key:
        raise MissingApiKeyError("MUSE_API_KEY is not set (see .env.example)")
    return OpenAI(api_key=api_key, base_url=os.environ.get("MUSE_BASE_URL", DEFAULT_BASE_URL))
