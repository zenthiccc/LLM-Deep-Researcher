from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from clarifier_agent import clarifier_agent, NUM_QUESTIONS
from llm_config import TRACING_ENABLED
from sources import SearchContext, SearchResult, Source, gather_sources, sources_from_annotations
from citations import apply_citations
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

    async def run(self, query: str, clarifications: list[tuple[str, str]] | None = None, citation_style: str = "ieee"):
        """ Run the deep research process, yielding ("status", text) updates and finally ("report", markdown) """
        context = format_clarifications(clarifications)
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id) if TRACING_ENABLED else nullcontext():
            if TRACING_ENABLED:
                yield "status", f"Starting research. Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            else:
                yield "status", "Starting research..."
            search_plan = await self.plan_searches(query, context)
            yield "status", f"Searches planned, running {len(search_plan.searches)} searches..."
            search_results = await self.perform_searches(search_plan)
            yield "status", "Searches complete, gathering source details..."
            sources = await gather_sources(search_results)
            yield "status", f"Found {len(sources)} sources, writing report..." if sources else "Writing report..."
            report = await self.write_report(query, context, search_results, sources)
            yield "report", apply_citations(report.markdown_report, sources, citation_style)

    async def plan_searches(self, query: str, context: str = "") -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        result = await Runner.run(planner_agent, f"Query: {query}{context}")
        return result.final_output

    async def perform_searches(self, search_plan: WebSearchPlan) -> list[SearchResult]:
        """ Perform the searches to perform for the query, dropping any that fail """
        tasks = [self.search(item) for item in search_plan.searches]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, SearchResult) and r.summary]

    async def search(self, item: WebSearchItem) -> SearchResult:
        """ Perform a search for the query, keeping the sources the search tool found """
        input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
        context = SearchContext()
        result = await Runner.run(search_agent, input_message, context=context)
        return SearchResult(summary=result.final_output, sources=context.sources + sources_from_annotations(result.new_items))

    async def write_report(self, query: str, context: str, search_results: list[SearchResult], sources: list[Source]) -> ReportData:
        """ Write the report for the query, giving each search summary the numbers of its sources """
        blocks = []
        for i, r in enumerate(search_results, start=1):
            ids = sorted({s.id for s in r.sources})
            blocks.append(f"Search {i} (sources: {', '.join(f'[{n}]' for n in ids) or 'none'}):\n{r.summary}")
        source_list = "\n".join(f"[{s.id}] {s.title} ({s.site_name})" for s in sources) or "No sources available."
        input_message = f"Original query: {query}{context}\n\nSources:\n{source_list}\n\nSummarized search results:\n\n" + "\n\n".join(blocks)
        result = await Runner.run(writer_agent, input_message)
        return result.final_output
