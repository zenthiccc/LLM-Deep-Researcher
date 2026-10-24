from pydantic import BaseModel, Field
from agents import Agent
from llm_config import get_model, output_schema

NUM_QUESTIONS = 3

INSTRUCTIONS = f"""
You are a research assistant. Before researching a user's query, ask {NUM_QUESTIONS} short clarifying
questions that would most change which web searches you run and how the final report is written.
Good questions cover things like scope or focus, time frame or region, and the intended audience or purpose.
Do not ask anything the query already answers. Keep each question to one sentence.
"""


class ClarifyingQuestions(BaseModel):
    questions: list[str] = Field(description=f"Exactly {NUM_QUESTIONS} short clarifying questions about the query.")


clarifier_agent = Agent(name="Clarifier Agent", instructions=INSTRUCTIONS, model=get_model(), output_type=output_schema(ClarifyingQuestions))
