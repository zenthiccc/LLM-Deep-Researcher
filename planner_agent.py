from pydantic import BaseModel, Field
from agents import Agent
import os
from dotenv import load_dotenv
from llm_config import get_model, output_schema
load_dotenv(override=True)

HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 5))


INSTRUCTIONS = f"""
You are a research assistant. Given a user query, come up with a set of web searches
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for.
The query may come with clarifications from the user. When it does, tailor the searches to the
stated scope, time frame, region and audience. For anything left unanswered, use sensible defaults.
"""

class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")

planner_agent = Agent(name="Planner Agent", instructions=INSTRUCTIONS, model=get_model(), output_type=output_schema(WebSearchPlan))
