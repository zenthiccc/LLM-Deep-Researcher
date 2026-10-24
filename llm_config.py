from agents import OpenAIChatCompletionsModel, AgentOutputSchema, set_tracing_disabled
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os

load_dotenv(override=True)

PROVIDER = os.getenv("MODEL_PROVIDER", "openai").lower()
if PROVIDER not in ("openai", "gemini"):
    raise ValueError(f"MODEL_PROVIDER must be 'openai' or 'gemini', got '{PROVIDER}'")

DEFAULT_MODELS = {"openai": "gpt-5.4-mini", "gemini": "gemini-3.5-flash-lite"}
MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", DEFAULT_MODELS[PROVIDER])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")

if PROVIDER == "openai" and not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("MODEL_PROVIDER=openai requires OPENAI_API_KEY to be set")
if PROVIDER == "gemini" and not GEMINI_API_KEY:
    raise RuntimeError("MODEL_PROVIDER=gemini requires GEMINI_API_KEY (or GOOGLE_API_KEY) to be set")

TRACING_ENABLED = PROVIDER == "openai"
if not TRACING_ENABLED:
    set_tracing_disabled(True)

_gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY) if PROVIDER == "gemini" else None


def get_model():
    """ Return the model for agents: a model name for OpenAI, or a Chat Completions model for Gemini """
    if PROVIDER == "gemini":
        return OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=_gemini_client)
    return MODEL_NAME


def output_schema(output_type):
    """ Gemini's OpenAI-compatible endpoint is unreliable with strict JSON schemas, so relax them there """
    if PROVIDER == "gemini":
        return AgentOutputSchema(output_type, strict_json_schema=False)
    return output_type
