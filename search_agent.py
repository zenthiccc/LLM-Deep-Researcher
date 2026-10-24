from agents import Agent, WebSearchTool, ModelSettings
from llm_config import PROVIDER, get_model

INSTRUCTIONS = """
You are a research assistant. Given a search term, you search the web for that term and
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 words.
Capture the main points and be succinct. Reply only with the summary.
"""

settings = ModelSettings(tool_choice="required")

if PROVIDER == "gemini":
    from gemini_search import web_search
    tools = [web_search]
else:
    tools = [WebSearchTool()]

search_agent = Agent(name="Search Agent", instructions=INSTRUCTIONS, tools=tools, model=get_model(), model_settings=settings)
