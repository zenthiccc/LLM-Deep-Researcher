from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from clarifier_agent import clarifier_agent, NUM_QUESTIONS
from llm_config import TRACING_ENABLED
from sources import SearchContext, SearchResult, Source, error_reason, gather_sources, sources_from_annotations
from citations import apply_citations
from usage import QuotaError, meter
from openai import RateLimitError
from contextlib import nullcontext
from dataclasses import dataclass
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


@dataclass
class Progress:
    """ A run's steps: labels[i] names each step (finished ones say what they found), current is the step in progress """
    labels: list[str]
    current: int
    part: float = 0.0
    trace_url: str = ""

    @property
    def fraction(self) -> float:
        return min((self.current + self.part) / len(self.labels), 1.0)

    def __str__(self) -> str:
        return self.labels[min(self.current, len(self.labels) - 1)] + "..."


def search_status(results: list[SearchResult]) -> str:
    """ "2 of 3 searches found web sources (429 RESOURCE_EXHAUSTED ...)" """
    found = sum(1 for r in results if r.sources)
    errors = list(dict.fromkeys(e for r in results for e in r.errors))
    reason = f" ({'; '.join(errors)})" if errors else ""
    return f"{found} of {len(results)} searches found web sources{reason}"


def no_references_note(results: list[SearchResult]) -> str:
    """ The References section for a report written without any web sources, saying why """
    errors = list(dict.fromkeys(e for r in results for e in r.errors))
    reason = f"The web search failed: {'; '.join(errors)}." if errors else "The searches didn't return any source links."
    return f"\n\n## References\n\n*No references. {reason} This report is based only on the model's own knowledge, so check its claims.*\n"


MEMORY_BANNER = "> *Written from the model's memory, without web search. Facts may be out of date, so check them before relying on them.*\n\n"
MEMORY_NOTE = "\n\n## References\n\n*No references. Web search was off for this report, so it is based only on the model's own knowledge.*\n"


def quota_error(reason: str | None = None, clarify: bool = True) -> QuotaError:
    """ A QuotaError with the notice, saying whether a run without web search still fits """
    memory_ok = meter.check_can_run(clarify=clarify, web_search=False) is None
    notice = meter.quota_notice(reason)
    if memory_ok:
        notice += "\n\nYou can still get a report written from the model's memory, without web sources."
    return QuotaError(notice, memory_ok)


class ResearchManager:

    async def clarify(self, query: str, web_search: bool = True) -> list[str]:
        """ Generate exactly NUM_QUESTIONS clarifying questions for the query; QuotaError if the quota can't cover a run """
        blocked = meter.check_can_run(web_search=web_search)
        if blocked:
            raise quota_error(blocked)
        try:
            result = await Runner.run(clarifier_agent, f"Query: {query}")
        except RateLimitError as e:
            if not meter.enabled:
                raise
            raise quota_error() from e
        questions = [q.strip() for q in result.final_output.questions if q.strip()][:NUM_QUESTIONS]
        return questions + FALLBACK_QUESTIONS[len(questions):NUM_QUESTIONS]

    async def run(self, query: str, clarifications: list[tuple[str, str]] | None = None, citation_style: str = "ieee", web_search: bool = True):
        """
        Run the deep research process, yielding ("status", Progress) updates and finally ("report", markdown).
        Raises QuotaError when the Gemini quota can't cover the run. Without web_search the writer works from
        the model's own knowledge, following the planner's topics.
        """
        blocked = meter.check_can_run(clarify=False, web_search=web_search)
        if blocked:
            raise quota_error(blocked, clarify=False)
        context = format_clarifications(clarifications)
        start = meter.snapshot()
        trace_id = gen_trace_id()
        trace_url = f"https://platform.openai.com/traces/trace?trace_id={trace_id}" if TRACING_ENABLED else ""
        with trace("Research trace", trace_id=trace_id) if TRACING_ENABLED else nullcontext():
            try:
                if web_search:
                    async for update in self._research(query, context, citation_style, trace_url):
                        yield update
                    meter.record_run(start)
                else:
                    async for update in self._write_from_memory(query, context, trace_url):
                        yield update
            except RateLimitError as e:
                if not meter.enabled:
                    raise
                raise quota_error(clarify=False) from e

    async def _research(self, query: str, context: str, citation_style: str, trace_url: str):
        """ Plan, search the web, gather sources and write the cited report """
        steps = ["Planning the searches", "Searching the web", "Gathering source details", "Writing the report"]
        yield "status", Progress(steps.copy(), 0, trace_url=trace_url)
        search_plan = await self.plan_searches(query, context)
        total = len(search_plan.searches)
        steps[0] = f"Planned {total} search{'' if total == 1 else 'es'}"
        yield "status", Progress(steps.copy(), 1, trace_url=trace_url)
        tasks = [asyncio.create_task(self.search_safely(item)) for item in search_plan.searches]
        for done, next_done in enumerate(asyncio.as_completed(tasks), start=1):
            await next_done
            yield "status", Progress(steps[:1] + [f"Searching the web, {done} of {total} done"] + steps[2:], 1, done / total, trace_url)
        search_results = [t.result() for t in tasks]
        steps[1] = search_status(search_results)
        yield "status", Progress(steps.copy(), 2, trace_url=trace_url)
        sources = await gather_sources(search_results)
        steps[2] = f"Found {len(sources)} source{'' if len(sources) == 1 else 's'}" if sources else "No web sources found"
        yield "status", Progress(steps.copy(), 3, trace_url=trace_url)
        report = await self.write_report(query, context, [r for r in search_results if r.summary], sources)
        markdown = apply_citations(report.markdown_report, sources, citation_style)
        yield "report", markdown if sources else markdown.rstrip() + no_references_note(search_results)

    async def _write_from_memory(self, query: str, context: str, trace_url: str):
        """ Plan the topics, then write the report from the model's own knowledge """
        steps = ["Planning the outline", "Writing the report from the model's memory"]
        yield "status", Progress(steps.copy(), 0, trace_url=trace_url)
        plan = await self.plan_searches(query, context)
        steps[0] = f"Planned {len(plan.searches)} topics"
        yield "status", Progress(steps.copy(), 1, trace_url=trace_url)
        topics = "\n".join(f"- {item.query}: {item.reason}" for item in plan.searches)
        input_message = f"Original query: {query}{context}\n\nNo web search was done for this report. Topics to cover:\n{topics}"
        result = await Runner.run(writer_agent, input_message)
        markdown = apply_citations(result.final_output.markdown_report, [], "ieee")
        yield "report", MEMORY_BANNER + markdown.rstrip() + MEMORY_NOTE

    async def plan_searches(self, query: str, context: str = "") -> WebSearchPlan:
        """ Plan the searches to perform for the query """
        result = await Runner.run(planner_agent, f"Query: {query}{context}")
        return result.final_output

    async def search_safely(self, item: WebSearchItem) -> SearchResult:
        """ Perform a search; one that fails comes back empty with its error """
        try:
            return await self.search(item)
        except Exception as e:
            return SearchResult(summary="", sources=[], errors=[error_reason(e)])

    async def search(self, item: WebSearchItem) -> SearchResult:
        """ Perform a search for the query, keeping the sources the search tool found """
        input_message = f"Search term: {item.query}\nReason for searching: {item.reason}"
        context = SearchContext()
        result = await Runner.run(search_agent, input_message, context=context)
        return SearchResult(summary=result.final_output, sources=context.sources + sources_from_annotations(result.new_items), errors=context.errors)

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
