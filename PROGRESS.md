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
| V-live | pending | | Verification steps 2–5 need real API keys |

## Open questions
- Does `gemini-3.5-flash-lite` support Google Search grounding and `tool_choice=required` on the compat endpoint? Confirm on first live run.

## Log
- 2026-10-24 — Plan approved; tracking docs created.
- 2026-10-24 — Phases 1–6 implemented. Offline smoke tests pass for both providers (wiring, tool selection, clarification formatting/padding, UI build, missing-key error). Live runs not yet done (no `.env`).
- 2026-10-24 — Decided: no separate `SEARCH_MODEL_NAME`; grounding uses `DEFAULT_MODEL_NAME`. Removed email and push notification features.
