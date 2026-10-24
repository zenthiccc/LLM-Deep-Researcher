# AGENTS.md

Deep research app: asks the user 3 clarifying questions, plans web searches tuned to the answers, runs them in parallel, and writes a long markdown report. Gradio UI on the `openai-agents` SDK, switchable between OpenAI and Google Gemini.

## Commands
- Install: `uv sync` (Python 3.12, uv-managed; add deps with `uv add`, never pip)
- Run the UI: `uv run python app.py` (the minimal UI is `simple.py`)
- Config: copy `.env.example` to `.env`. Never commit `.env`.
- There is no test suite. To check that the code loads without real keys:
  `MODEL_PROVIDER=gemini GEMINI_API_KEY=x OPENAI_API_KEY=x uv run python -c "import app, research_manager"` (repeat with `MODEL_PROVIDER=openai`)

## Architecture
```
app.py (Gradio chat UI)
  └─ ResearchManager (research_manager.py)
       clarify(query)        → clarifier_agent  → 3 questions
       run(query, Q&A pairs) → planner_agent    → WebSearchPlan
                             → search_agent ×N  (in parallel; a failed search is dropped) → SearchResult(summary, sources)
                             → gather_sources   (sources.py: resolve redirects, fetch page metadata, dedupe, number)
                             → writer_agent     → ReportData with [n] citation markers
                             → apply_citations  (citations.py: IEEE or APA in-text + reference list)
```
- `llm_config.py` is the single source of truth for the provider. `MODEL_PROVIDER=openai|gemini` (default `openai`), `DEFAULT_MODEL_NAME` overrides the model (defaults: `gpt-5.4-mini` / `gemini-3.5-flash-lite`). It fails fast at import when the provider's API key is missing.
- Gemini runs through its OpenAI-compatible endpoint (`OpenAIChatCompletionsModel`). OpenAI tracing is turned off on Gemini.
- Web search: OpenAI uses the hosted `WebSearchTool`. Gemini uses the `web_search` function tool in `gemini_search.py` (Google Search grounding via `google-genai`), because hosted OpenAI tools don't work with Gemini.
- `ResearchManager.run` yields `("status", text)` progress updates, then one `("report", markdown)`.
- Clarification answers are formatted by `format_clarifications()` and passed to the planner and the writer only. Blank answers are left out.
- References: the Gemini `web_search` tool records sources in the run context (`SearchContext`); OpenAI sources come from `url_citation` annotations. Reference entries are formatted in Python, never by an LLM, so nothing is invented. The writer only places `[n]` markers and must not write its own references section (one it adds anyway is stripped). `citation_style` is `"ieee"` (default) or `"apa"`. No sources → the References section is a note giving the reason (search errors are recorded in `SearchContext.errors` / `SearchResult.errors`), and the status line reports how many searches found sources. Never fail silently.

## Conventions
- One agent per file (`*_agent.py`): an `INSTRUCTIONS` string, Pydantic output models, and a module-level `Agent(...)`.
- Always use `model=get_model()`, and wrap structured outputs as `output_type=output_schema(Model)` (Gemini needs non-strict schemas). Don't read `DEFAULT_MODEL_NAME` in agent files.
- Use one model setting for everything. Don't add per-agent or search-specific model variables (`SEARCH_MODEL_NAME` was rejected).
- Email and push notifications were removed on purpose. Don't add them back.
- UI styling lives in `styles.py`: color tokens on `:root`, dark theme under `.dark`, element ids prefixed `dr-`. Hidden Gradio components are not rendered, so `:has(#dr-home)` detects the home screen.

## Workflow
- Ask before making architecture decisions; the user wants to be consulted on them.
- Track work in `PLAN.md` (tasks with checkboxes) and `PROGRESS.md` (status table and log). Update both when a task is done.
- Commits follow Conventional Commits, one logical change per commit, on a feature branch off `master`. Don't push unless asked.
