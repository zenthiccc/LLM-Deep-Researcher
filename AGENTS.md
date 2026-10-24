# AGENTS.md

Deep research app: asks the user 3 clarifying questions, plans web searches tuned to the answers, runs them in parallel, and writes a long markdown report. Gradio UI on the `openai-agents` SDK, switchable between OpenAI and Google Gemini.

## Commands
- Install: `uv sync` (Python 3.12, uv-managed; add deps with `uv add`, never pip)
- Run the UI: `uv run python app.py` (the minimal UI is `simple.py`)
- Config: copy `.env.example` to `.env`. Never commit `.env`.
- There is no test suite. To check that the code loads without real keys:
  `MODEL_PROVIDER=gemini GEMINI_API_KEY=x OPENAI_API_KEY=x uv run python -c "import app, research_manager"` (repeat with `MODEL_PROVIDER=openai`).
  `load_dotenv(override=True)` lets a local `.env` override these variables, so run the check from a copy of the `*.py` files without `.env` (`uv run --project <repo> python ...`).
  Don't import `simple.py` in checks: it launches its server at import.
- Never spend the user's quota in checks: the user runs a free-tier Gemini key. Mock agents and HTTP (the `openai` client uses `httpx2`, so mock with `httpx2.MockTransport`) and ask before any live call.

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
- `ResearchManager.run` yields `("status", Progress)` updates (step labels, the current step, a fill fraction; `str()` gives a plain line), then one `("report", markdown)`. `app.py` renders `Progress` as a step card with a bar.
- Memory-only runs (`run(..., web_search=False)`): planner + writer, no search agents. The writer covers the planner's topics from its own knowledge; the report starts with a "written from the model's memory" banner and ends with a no-references note. Offered only through the **Continue without web search** button on a quota notice, when the remaining calls still cover such a run.
- Clarification answers are formatted by `format_clarifications()` and passed to the planner and the writer only. Blank answers are left out.
- References: the Gemini `web_search` tool records sources in the run context (`SearchContext`); OpenAI sources come from `url_citation` annotations. Reference entries are formatted in Python, never by an LLM, so nothing is invented. The writer only places `[n]` markers and must not write its own references section (one it adds anyway is stripped). `citation_style` is `"ieee"` (default) or `"apa"`. No sources → the References section is a note giving the reason (search errors are recorded in `SearchContext.errors` / `SearchResult.errors`), and the status line reports how many searches found sources. Never fail silently.
- Usage (Gemini only, `usage.py`): `meter` counts every Gemini HTTP request (httpx hooks on the client in `llm_config.py`, `max_retries=0`) and every grounding call (`meter.acquire("search")` in `gemini_search.py`), throttles to `GEMINI_RPM`, and learns from 429s. `ResearchManager` refuses to start when `meter.check_can_run()` gives a reason: `clarify` and `run` raise `QuotaError`, whose `memory_ok` says whether a memory-only run still fits. Each web run's cost is recorded (memory-only runs are a fixed 2 calls). Counts persist through a store: `.usage.json` (gitignored) by default, or Upstash Redis over its REST API when `UPSTASH_REDIS_REST_URL`/`UPSTASH_REDIS_REST_TOKEN` are set (needed on Render's free plan, whose disk is wiped on restart). The state is read on first use, Upstash writes go out on a background thread, and a failed first read turns off saving so it can't overwrite the saved counts. Remaining quota is an estimate, since Google doesn't report it.

- Deployment: `render.yaml` (Render Blueprint, free plan). Gradio takes its host and port from `GRADIO_SERVER_NAME`/`GRADIO_SERVER_PORT`. `APP_USERNAME` + `APP_PASSWORD` turn on Gradio's login (both or neither).

## Conventions
- One agent per file (`*_agent.py`): an `INSTRUCTIONS` string, Pydantic output models, and a module-level `Agent(...)`.
- Always use `model=get_model()`, and wrap structured outputs as `output_type=output_schema(Model)` (Gemini needs non-strict schemas). Don't read `DEFAULT_MODEL_NAME` in agent files.
- Use one model setting for everything. Don't add per-agent or search-specific model variables (`SEARCH_MODEL_NAME` was rejected).
- Email and push notifications were removed on purpose. Don't add them back.
- UI styling lives in `styles.py`: color tokens on `:root`, dark theme under `.dark`, element ids prefixed `dr-`. Hidden Gradio components are not rendered, so `:has(#dr-home)` detects the home screen. The login page doesn't get the app's CSS (it comes with the config, which needs a login), so `LOGIN_HTML` (passed as `auth_message`, which Gradio renders as HTML) carries its own `<style>` built from the shared `TOKENS_CSS`.

## Workflow
- Ask before making architecture decisions; the user wants to be consulted on them.
- Track work in `PLAN.md` (tasks with checkboxes) and `PROGRESS.md` (status table and log). Update both when a task is done.
- Commits follow Conventional Commits, one logical change per commit, on a feature branch off `master`. Don't push unless asked.
