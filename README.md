---
title: deep_research
app_file: app.py
sdk: gradio
sdk_version: 6.30.0
---

# Deep Research

Asks 3 clarifying questions about your query, plans web searches tuned to your answers, runs them in parallel, and writes a long markdown report with references in IEEE or APA style.

## Setup
```bash
uv sync
cp .env.example .env   # then fill in keys
uv run python app.py
```

## Providers
Set `MODEL_PROVIDER` in `.env`:

| Provider | Required key | Default model | Web search |
|---|---|---|---|
| `openai` (default) | `OPENAI_API_KEY` | `gpt-5.4-mini` | OpenAI hosted `WebSearchTool` |
| `gemini` | `GEMINI_API_KEY` | `gemini-3.5-flash-lite` | Google Search grounding (`gemini_search.py`) |

Override the model with `DEFAULT_MODEL_NAME`. Gemini runs through its OpenAI-compatible endpoint (`llm_config.py`). OpenAI tracing is turned off when using Gemini.

## Clarifying questions
After you click **Investigate**, three questions appear. Answer any of them (blank answers are skipped), then click **Start research**. Your answers shape both the search plan and the report. **Skip clarifications** runs the research on the raw query. `simple.py` always skips.

## References
Pick **IEEE** or **APA** next to the Start research button. Sources come from the search tools (OpenAI citations or Gemini grounding), and each page is fetched to read its title, authors, publication date and site name. Fields a page doesn't provide are left out (APA shows `n.d.` for a missing date). Duplicate pages are merged. The writer marks claims with `[n]`, and `citations.py` turns those into IEEE numbers or APA author-date citations and adds the reference list. The report always ends with a References section. If no sources were found, that section says so and gives the reason (for example `429 RESOURCE_EXHAUSTED` when the Gemini Google Search quota is used up), and the progress line shows how many searches found web sources.
