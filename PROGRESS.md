# PROGRESS

See `PLAN.md` for task definitions.

| Task | Status | Date | Notes |
|---|---|---|---|
| T0.1 | done | 2026-10-24 | |
| T0.2 | done | 2026-10-24 | |
| T1.1 | done | 2026-10-24 | google-genai 2.33.0 added |
| T1.2 | done | 2026-10-24 | `llm_config.py`; fails fast on missing key |
| T1.3 | done | 2026-10-24 | |
| T1.4 | done | 2026-10-24 | Applied up front via `output_schema()` (needs live check) |
| T1.5 | done | 2026-10-24 | |
| T2.1 | done | 2026-10-24 | Uses same `MODEL_NAME` for grounding calls |
| T2.2 | done | 2026-10-24 | SDK resets `tool_choice` after the first tool call, so `required` is safe |
| T2.3 | done | 2026-10-24 | |
| T3.1 | done | 2026-10-24 | |
| T3.2 | done | 2026-10-24 | Pads with fallback questions |
| T3.3 | done | 2026-10-24 | |
| T4.1 | done | 2026-10-24 | |
| T4.2 | done | 2026-10-24 | |
| T5.1 | done | 2026-10-24 | |
| T5.2 | done | 2026-10-24 | |
| T5.3 | done | 2026-10-24 | No change needed |
| T6.1 | done | 2026-10-24 | |
| T6.2 | done | 2026-10-24 | |
| T7.1 | done | 2026-10-24 | Email/push not needed |
| T7.2 | done | 2026-10-24 | |
| T8.1 | done | 2026-10-24 | Checked with mocked agents via headless screenshots |
| T8.2 | done | 2026-10-24 | |
| T8.3 | done | 2026-10-24 | `simple.py` updated to match |
| T9.1 | done | 2026-10-24 | Gemini tool gets `SearchContext`; OpenAI via annotations |
| T9.2 | done | 2026-10-24 | Tested on arXiv, Wikipedia, Guardian, GitHub redirect, dead domain |
| T9.3 | done | 2026-10-24 | IEEE renumbers by first citation; APA a/b suffixes for same author-year |
| T9.4 | done | 2026-10-24 | |
| T9.5 | done | 2026-10-24 | Segmented IEEE/APA control in the questions panel |
| T9.6 | done | 2026-10-24 | |
| T9.7 | done | 2026-10-24 | Live Gemini run: grounding returned 429, report now ends with a no-references note giving the reason |
| T10.1 | done | 2026-10-24 | Offline: RPM throttle, PT midnight/month rollover, 429 per-minute vs daily |
| T10.2 | done | 2026-10-24 | Checked through the real `AsyncOpenAI` client with an `httpx2` mock: one 429 is counted once, not retried |
| T10.3 | done | 2026-10-24 | |
| T10.4 | done | 2026-10-24 | Mocked runs: blocked before any call; mid-run 429 shows a notice |
| T10.5 | done | 2026-10-24 | |
| T10.6 | done | 2026-10-24 | |
| T11.1 | done | 2026-10-24 | |
| T11.2 | done | 2026-10-24 | Mocked runs: memory run makes only planner + writer calls; stray `[n]` and writer references stripped |
| T11.3 | done | 2026-10-24 | Mocked: blocked at questions → memory questions; blocked at run → memory run with the same answers; calls used up → no button |
| T11.4 | done | 2026-10-24 | Screenshots light/dark/500px. Headless Chrome doesn't advance CSS animations, so the bar fill animation was checked on a static page |
| T11.5 | done | 2026-10-24 | |
| T11.6 | done | 2026-10-24 | Both providers; the chip truncates on narrow screens, full name on hover |
| V-live | partial | 2026-10-24 | Gemini plain calls work; Google Search grounding returns 429 RESOURCE_EXHAUSTED on the user's key |

## Open questions
- Gemini Google Search grounding returns `429 RESOURCE_EXHAUSTED` on the current key while plain calls work. Needs billing enabled or the quota to reset before grounded sources can be checked live.

## Log
- 2026-10-24 — Plan approved; tracking docs created.
- 2026-10-24 — Phases 1–6 implemented. Offline smoke tests pass for both providers (wiring, tool selection, clarification formatting/padding, UI build, missing-key error). Live runs not yet done (no `.env`).
- 2026-10-24 — Decided: no separate `SEARCH_MODEL_NAME`; grounding uses `DEFAULT_MODEL_NAME`. Removed email and push notification features.
- 2026-10-24 — Chat-style UI redesign (Phase 8).
- 2026-10-24 — References in IEEE/APA (Phase 9). Checked offline and with real page fetches; not yet run against live models.
- 2026-10-24 — Two user runs had no references. Cause: every grounded search failed with 429 and the tool swallowed the error, so summaries came from model memory. Errors are now recorded and shown in the status and the report (T9.7).
- 2026-10-24 — Usage meter and rate limiting for the Gemini free tier (Phase 10). Tested offline only; no quota spent.
- 2026-10-24 — Memory-only reports when the search quota is used up, and a step-card progress indicator (Phase 11). Tested offline only; no quota spent.
