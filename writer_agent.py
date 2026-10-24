from pydantic import BaseModel, Field
from agents import Agent
from llm_config import get_model, output_schema

INSTRUCTIONS = """
You are a senior researcher tasked with writing a cohesive report for a research query.
You will be provided with the original query, and some research.
Generate a comprehensive report based on the research and the query.
The final output should be in markdown format, and it should be lengthy and detailed. Aim 
for 5-10 pages of content, at least 1000 words.
If the user gave clarifications, tailor the report's focus, depth and audience to their answers.
The research comes with a numbered list of sources. Support factual claims with citation markers
that use those numbers, like [3] or [1][4], placed before the sentence's final punctuation.
Only use numbers from the list. Do not write a references, sources or bibliography section;
one is added automatically. If no sources are listed, do not use citation markers.
If the input says no web search was done, write from your own knowledge, covering the listed topics.
Don't invent statistics, quotes or recent events, and say where facts may have changed since your training data.
"""


class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The final report")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")


writer_agent = Agent(name="Writer Agent", instructions=INSTRUCTIONS, model=get_model(), output_type=output_schema(ReportData))
