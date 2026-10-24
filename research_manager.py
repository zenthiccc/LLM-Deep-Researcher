from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from email_agent import email_agent
from clarifier_agent import clarifier_agent, NUM_QUESTIONS
from llm_config import TRACING_ENABLED
from contextlib import nullcontext
import asyncio

FALLBACK_QUESTIONS = [
    "What specific aspect of this topic matters most to you?",
    "Is there a particular time frame or region to focus on?",
    "Who is the report for, and how will you use it?",
]


def format_clarifications(clarifications: list[tuple[str, str]] | None) -> str:
    """ Format answered clarifying questions as a block for agent input, or an empty string """
    answered = [(q, a.strip()) for q, a in clarifications or [] if a and a.strip()]
    if not answered:
        return ""
    lines = [f"Q: {q}\nA: {a}" for q, a in answered]
    return "\nClarifications from the user:\n" + "\n".join(lines)


class ResearchManager:

    async def clarify(self, query: str) -> list[str]:
        """ Generate exactly NUM_QUESTIONS clarifying questions for the query """
        result = await Runner.run(clarifier_agent, f"Query: {query}")
        questions = [q.strip() for q in result.final_output.questions if q.strip()][:NUM_QUESTIONS]
        return questions + FALLBACK_QUESTIONS[len(questions):NUM_QUESTIONS]

    async def run(self, query: str, clarifications: list[tuple[str, str]] | None = None):
        """ Run the deep research process, yielding the status updates and the final report"""
        context = format_clarifications(clarifications)
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id) if TRACING_ENABLED else nullcontext():
            if TRACING_ENABLED:
                yield f"Starting research. Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            else:
                yield "Starting research..."
            search_plan = await self.plan_searches(query, context)
            yield f"Searches planned, starting {len(search_plan.searches)} searches..."
            search_results = await self.perform_searches(search_plan)
            yield "Searches complete, writing report..."
            report = await self.write_report(query, context, search_results)
            yield "Report written, sending email..."
            await self.send_email(report)
            yield "Email sent, research complete"
            yield report.markdown_report

    async def plan_searches(self, query: str, context: str = "") -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        result = await Runner.run(planner_agent, f"Query: {query}{context}")
        return result.final_output

    async def perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        """ Perform the searches to perform for the query, dropping any that fail """
        tasks = [self.search(item) for item in search_plan.searches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, str) and r]

    async def search(self, item: WebSearchItem) -> str | None:
        """ Perform a search for the query """
        input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
        result = await Runner.run(search_agent, input_message)
        return result.final_output

    async def write_report(self, query: str, context: str, search_results: list[str]) -> ReportData:
        """ Write the report for the query """
        input_message = f"Original query: {query}{context}\nSummarized search results: {search_results}"
        result = await Runner.run(writer_agent, input_message)
        return result.final_output

    async def send_email(self, report: ReportData) -> None:
        await Runner.run(email_agent, report.markdown_report)
