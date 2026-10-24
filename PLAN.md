# PLAN — Gemini support + clarifying questions

## Context
The base app (Gradio UI → `ResearchManager` → planner → parallel search agents → writer → email) ran on the `openai-agents` SDK and is hard-wired to OpenAI (`gpt-5.4-mini`, OpenAI-hosted `WebSearchTool`, OpenAI tracing).

Goals:
1. Run on Google Gemini models, switchable with OpenAI via env.
2. Ask the user 3 clarifying questions (skippable) before researching, and use the answers to tune search planning and the final report.

## Architecture decisions
| Topic | Decision |
|---|---|
| Gemini wiring | Keep `openai-agents`; use Gemini's OpenAI-compatible endpoint via `AsyncOpenAI` + `OpenAIChatCompletionsModel` |
| Providers | `MODEL_PROVIDER=gemini\|openai` (default `openai`) |
| Default Gemini model | `gemini-3.5-flash-lite` (override with `DEFAULT_MODEL_NAME`) |
| Search on Gemini | `function_tool` calling `google-genai` with Google Search grounding; returns text + source URLs |
| Tracing | Disabled on Gemini; trace link hidden |
| Clarifications | 3 questions; two-step UI with **Skip clarifications**; answers go to planner + writer |
| Tracking | `PLAN.md` (this file) + `PROGRESS.md` (status log) |

## Tasks

### Phase 0 — Tracking docs
- [x] T0.1 Create `PLAN.md`
- [x] T0.2 Create `PROGRESS.md`

### Phase 1 — Provider abstraction
- [x] T1.1 Add `google-genai` to `pyproject.toml`; `uv sync`
- [x] T1.2 New `llm_config.py`: `PROVIDER`, `get_model()`, `TRACING_ENABLED`, fail-fast key check
- [x] T1.3 All agents use `model=get_model()`
- [x] T1.4 Non-strict output schema for Gemini (`AgentOutputSchema(..., strict_json_schema=False)`)
- [x] T1.5 `research_manager.py`: trace + trace link only when tracing enabled

### Phase 2 — Gemini web search
- [x] T2.1 New `gemini_search.py`: `web_search` function tool with Google Search grounding
- [x] T2.2 `search_agent.py` picks `WebSearchTool` (openai) or `web_search` (gemini)
- [x] T2.3 `perform_searches` tolerates individual search failures

### Phase 3 — Clarifying questions agent
- [x] T3.1 New `clarifier_agent.py` with `ClarifyingQuestions` output
- [x] T3.2 `ResearchManager.clarify(query)` → exactly 3 questions
- [x] T3.3 `ResearchManager.run(query, clarifications=None)` + `format_clarifications()`

### Phase 4 — Tune searches and report
- [x] T4.1 Planner input + instructions use clarifications
- [x] T4.2 Writer input + instructions use clarifications

### Phase 5 — Gradio UI
- [x] T5.1 `app.py` two-step flow: Investigate → questions → Start research / Skip
- [x] T5.2 `styles.py` CSS for `#dr-clarify`
- [x] T5.3 `simple.py` stays query-only (skip path)

### Phase 7 — Remove email/push
- [x] T7.1 Delete `email_agent.py`, `messenger.py`; drop email step from `ResearchManager`
- [x] T7.2 Remove `requests` dependency and email/Pushover env vars

### Phase 8 — Chat-style UI
- [x] T8.1 Chat-thread layout: greeting + composer on home, user bubble, questions and report as assistant messages, composer pinned at the bottom
- [x] T8.2 Warm palette with light/dark themes, serif reading text, suggestion chips
- [x] T8.3 `ResearchManager.run` yields `("status" | "report", text)` so progress and report render separately

### Phase 9 — References (APA / IEEE)
Decisions: user picks IEEE or APA per run in the UI (default IEEE); sources are captured as structured data and formatted in Python (the writer only places `[n]` markers); page metadata (author, date, site, title) is fetched for each source; no sources → no references section (revised in T9.7).
- [x] T9.1 `sources.py`: `Source` model, capture from the Gemini tool (run context) and OpenAI `url_citation` annotations
- [x] T9.2 Resolve redirects, fetch page metadata (meta tags + JSON-LD), dedupe, number
- [x] T9.3 `citations.py`: IEEE and APA entries, in-text citations, reference list
- [x] T9.4 Writer cites with `[n]` markers; `ResearchManager.run(..., citation_style)`
- [x] T9.5 UI citation-style selector
- [x] T9.6 Docs: README, AGENTS.md
- [x] T9.7 Make missing references visible: record search errors, show "N of M searches found web sources" in the status, always end the report with a References section (a note with the reason when there are no sources)

### Phase 10 — Usage meter and rate limiting (Gemini)
Decisions: limits come from `.env` (`GEMINI_RPM`, `GEMINI_RPD`, `GEMINI_SEARCH_LIMIT`, `GEMINI_SEARCH_PERIOD`); throttle to RPM and refuse to start a run that the remaining quota can't cover; usage line under each report + counter in the top bar; Gemini only. Google doesn't expose remaining quota, so counts are local.
- [x] T10.1 `usage.py`: persisted counts (midnight-PT day, monthly search period), RPM throttle, 429 parsing, run-cost estimate, summaries
- [x] T10.2 Count every Gemini request via httpx hooks on the client; SDK retries off
- [x] T10.3 Count grounding calls in `gemini_search.py`
- [x] T10.4 Block clarify/run before spending when the quota can't cover a run; quota notice on a mid-run 429
- [x] T10.5 UI: top-bar counter and usage line under the report
- [x] T10.6 Docs: `.env.example`, README, AGENTS.md

### Phase 11 — Memory-only reports and progress card
Decisions: when the search quota is used up but calls are left, the quota notice offers **Continue without web search** (never automatic); a memory-only run is planner + writer (the planner's items become the topics to cover), and the report is marked as written from memory with a no-references note; progress is a card in the thread with a filling bar and a checklist of steps.
- [x] T11.1 `usage.py`: memory-only cost (2 calls + clarify), `check_can_run(web_search=...)`, `QuotaError.memory_ok`
- [x] T11.2 `ResearchManager.run(..., web_search)`: memory-only path; `QuotaError` raised instead of yielding the notice
- [x] T11.3 UI: button on the quota notice that resumes the blocked step (questions or run) without web search
- [x] T11.4 `Progress` updates (steps, current step, fraction; per-search count) and the step card with a bar; Gradio's own loading overlay hidden
- [x] T11.5 Docs: README, AGENTS.md
- [x] T11.6 Show the model in use: chip in the top bar, "Model:" line under each report

### Phase 12 — Deploy on Render
Decisions: Render Blueprint (`render.yaml`, free plan, uv build); optional login with Gradio auth from `APP_USERNAME`/`APP_PASSWORD`; usage counts in Upstash Redis (free, durable, REST over the existing `httpx`) when its env vars are set, else `.usage.json`.
- [x] T12.1 `usage.py`: `FileStore` / `UpstashStore`, chosen by env; lazy first read; background writes; no writes after a failed read
- [x] T12.2 `app.py`: optional login
- [x] T12.3 `render.yaml`, `.env.example`
- [x] T12.4 Docs: README "Deploy on Render", AGENTS.md
- [x] T12.5 Login page styled like the chat UI (mark, serif greeting, card form, accent button; light and dark)

### Phase 6 — Docs & config
- [x] T6.1 `.env.example`
- [x] T6.2 README setup for both providers

## Verification
1. `uv sync` succeeds.
2. `MODEL_PROVIDER=openai uv run python app.py` — unchanged behavior, trace link shown.
3. `MODEL_PROVIDER=gemini` — 3 questions appear; answering or skipping produces a report; no trace link.
4. `uv run python -c "import asyncio; from research_manager import ResearchManager; print(asyncio.run(ResearchManager().clarify('EV battery tech')))"` returns 3 questions.
5. Planner search terms reflect clarification constraints (e.g. "Europe, 2025 only").
6. Missing API key → clear startup error.
