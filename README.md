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

Override the model with `DEFAULT_MODEL_NAME`. The model in use is shown next to the name in the top bar and under each report. Gemini runs through its OpenAI-compatible endpoint (`llm_config.py`). OpenAI tracing is turned off when using Gemini.

## Clarifying questions
After you click **Investigate**, three questions appear. Answer any of them (blank answers are skipped), then click **Start research**. Your answers shape both the search plan and the report. **Skip clarifications** runs the research on the raw query. `simple.py` always skips.

## References
Pick **IEEE** or **APA** next to the Start research button. Sources come from the search tools (OpenAI citations or Gemini grounding), and each page is fetched to read its title, authors, publication date and site name. Fields a page doesn't provide are left out (APA shows `n.d.` for a missing date). Duplicate pages are merged. The writer marks claims with `[n]`, and `citations.py` turns those into IEEE numbers or APA author-date citations and adds the reference list. The report always ends with a References section. If no sources were found, that section says so and gives the reason (for example `429 RESOURCE_EXHAUSTED` when the Gemini Google Search quota is used up), and the progress line shows how many searches found web sources.

## Free-tier usage (Gemini)
Google doesn't report how much quota is left, so the app counts its own calls (`usage.py`) and compares them with the limits you copy into `.env` from AI Studio's Rate limits page: `GEMINI_RPM`, `GEMINI_RPD`, `GEMINI_SEARCH_LIMIT` and `GEMINI_SEARCH_PERIOD`. Calls you make elsewhere on the same project (for example in AI Studio) aren't counted.

- **Meter:** the top bar shows the calls left and about how many runs that allows. Each report ends with a usage line: calls today, searches, runs left and time until the daily reset (midnight Pacific time).
- **Rate limiting:** calls are spaced out to stay under `GEMINI_RPM`, and automatic retries are off because each retry uses up quota.
- **Blocking:** a run won't start when fewer calls or searches are left than one run needs. The estimate is the average of your last 5 runs, about 12 calls with 3 searches. A 429 from Google marks that quota as used up until it resets.
- **Without web search:** when only the search quota is used up, the notice has a **Continue without web search** button. That run uses about 3 calls (questions, an outline, the report) and no searches. The report is written from the model's memory, says so at the top, and has no references.
- Counts are kept in `.usage.json` (not committed), or in Upstash Redis when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set (see Deploy on Render). Delete the file (or the `deep-research:usage` key) to reset the meter, for example after you enable billing.

## Deploy on Render
`render.yaml` sets up a free web service. Render's free plan wipes the disk on every restart, and the service sleeps after 15 idle minutes, so the usage counts are kept in a free Upstash Redis database instead.

1. Push the repo to GitHub.
2. Create a free database at [upstash.com](https://upstash.com) (Redis, any region near your Render region). From its **REST API** section, copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.
3. In Render: **New → Blueprint**, pick the repo. Render asks for the values marked `sync: false`: your `GEMINI_API_KEY`, a username and password (`APP_USERNAME`, `APP_PASSWORD`), your Gemini limits, and the two Upstash values.
4. Deploy. The app is at `https://<service>.onrender.com` and asks for the username and password. After it has slept, the first visit takes about a minute.

A shared link shows a preview card (title, description and `assets/preview.png`), even behind the login. The image link uses Render's own URL; with a custom domain, set `PUBLIC_URL` (e.g. `https://research.example.com`). Chat apps cache previews, so a link shared before a deploy may keep its old card for a while.

Without the login, anyone with the URL can use your Gemini quota. Set both `APP_USERNAME` and `APP_PASSWORD`, or neither (the app won't start with only one).

