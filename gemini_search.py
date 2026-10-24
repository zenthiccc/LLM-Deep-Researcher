from agents import function_tool
from google import genai
from google.genai import types
from llm_config import GEMINI_API_KEY, MODEL_NAME

_client = genai.Client(api_key=GEMINI_API_KEY)
_config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])


@function_tool
async def web_search(query: str) -> str:
    """
    Search the web with Google Search and return the findings with their source URLs

    Args:
        query: The search term to look up
    """
    try:
        response = await _client.aio.models.generate_content(model=MODEL_NAME, contents=query, config=_config)
    except Exception as e:
        return f"Search failed for '{query}': {e}"

    sources = []
    candidate = response.candidates[0] if response.candidates else None
    metadata = candidate.grounding_metadata if candidate else None
    for chunk in (metadata.grounding_chunks or []) if metadata else []:
        if chunk.web and chunk.web.uri:
            sources.append(f"- {chunk.web.title or chunk.web.uri}: {chunk.web.uri}")

    text = response.text or "No results found."
    if sources:
        text += "\n\nSources:\n" + "\n".join(sources)
    return text
