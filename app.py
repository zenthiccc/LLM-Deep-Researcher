import html
import os
import re
import gradio as gr
from dotenv import load_dotenv
from research_manager import Progress, ResearchManager
from clarifier_agent import NUM_QUESTIONS
from usage import QuotaError, meter
from llm_config import MODEL_NAME, PROVIDER_LABEL
from styles import CSS, JS, EXAMPLES, LOGIN_HTML, topbar_html, GREETING_HTML, ASSISTANT_LABEL_HTML

load_dotenv(override=True)

# Optional login: set both to require a sign-in (do this on any public deployment)
APP_USERNAME = os.getenv("APP_USERNAME", "").strip()
APP_PASSWORD = os.getenv("APP_PASSWORD", "").strip()
if bool(APP_USERNAME) != bool(APP_PASSWORD):
    raise RuntimeError("Set both APP_USERNAME and APP_PASSWORD to require a login, or neither")
AUTH = (APP_USERNAME, APP_PASSWORD) if APP_USERNAME else None


def status_html(text: str) -> str:
    """ Render a progress line with a pulsing dot, keeping any URL clickable """
    body = re.sub(r"(https?://\S+)", r'<a href="\1" target="_blank">trace</a>', html.escape(text))
    return f'<div class="dr-status"><span class="dr-dot"></span>{body}</div>'


CHECK_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'

CLARIFY_INTRO = "A few quick questions so I can focus the research. Answer any you like."
MEMORY_INTRO = "Web search is off for this report, so I'll write it from my own knowledge. A few quick questions so I can focus it. Answer any you like."


def progress_html(progress: Progress, previous: float = 0.0) -> str:
    """ Render a run's progress as a card: a bar that fills from the previous fraction, then the steps """
    items = []
    for i, label in enumerate(progress.labels):
        if i < progress.current:
            state, icon, text = "done", CHECK_SVG, label
        elif i == progress.current:
            state, icon, text = "active", "", label + "…"
        else:
            state, icon, text = "todo", "", label
        items.append(f'<li class="dr-step dr-step-{state}"><span class="dr-step-icon">{icon}</span><span>{html.escape(text)}</span></li>')
    trace = f'<a class="dr-progress-trace" href="{html.escape(progress.trace_url)}" target="_blank">View trace</a>' if progress.trace_url else ""
    bar = f'<div class="dr-progress-bar"><span style="--from: {previous:.0%}; --to: {progress.fraction:.0%}"></span></div>'
    return f'{ASSISTANT_LABEL_HTML}<div class="dr-progress">{bar}<ol class="dr-steps">{"".join(items)}</ol>{trace}</div>'


MODEL_LINE = f"Model: {MODEL_NAME} ({PROVIDER_LABEL})"
MODEL_CHIP = f'<span class="dr-model" title="{html.escape(MODEL_LINE)}, used for every step">{html.escape(MODEL_NAME)}</span>'


def current_topbar() -> str:
    return topbar_html(MODEL_CHIP, meter.compact_html())


with gr.Blocks(title="Deep Research") as ui:
    query_state = gr.State("")
    questions_state = gr.State([])
    # Whether this query's run uses web search, and what the "Continue without web search" button resumes
    # (None: ask the questions; otherwise the blocked run's clarifications and citation style)
    web_search_state = gr.State(True)
    resume_state = gr.State(None)

    topbar = gr.HTML(current_topbar())

    with gr.Column(elem_id="dr-thread"):
        with gr.Column(elem_id="dr-home") as home:
            gr.HTML(GREETING_HTML)

        user_message = gr.Markdown(visible=False, elem_id="dr-user-msg")

        with gr.Group(visible=False, elem_id="dr-clarify") as clarify_group:
            gr.HTML(ASSISTANT_LABEL_HTML)
            clarify_intro = gr.Markdown(CLARIFY_INTRO, elem_classes="dr-clarify-intro")
            question_labels, answer_boxes = [], []
            for i in range(NUM_QUESTIONS):
                question_labels.append(gr.Markdown(elem_classes="dr-question"))
                answer_boxes.append(gr.Textbox(show_label=False, container=False, placeholder="Your answer (optional)", elem_classes="dr-answer"))
            with gr.Row(elem_classes="dr-clarify-actions"):
                start_button = gr.Button("Start research", variant="primary", elem_id="dr-start", scale=0)
                skip_button = gr.Button("Skip", variant="secondary", elem_id="dr-skip", scale=0)
                citation_style = gr.Radio(
                    choices=[("IEEE", "ieee"), ("APA", "apa")],
                    value="ieee",
                    label="References",
                    elem_id="dr-style",
                    scale=0,
                )

        status = gr.HTML(elem_id="dr-status-wrap")
        report = gr.Markdown(elem_id="dr-report")
        memory_button = gr.Button("Continue without web search", variant="secondary", visible=False, elem_id="dr-memory", scale=0)
        usage_line = gr.HTML(elem_id="dr-usage-wrap")

    with gr.Column(elem_id="dr-composer-wrap"):
        with gr.Row(elem_id="dr-composer"):
            query_textbox = gr.Textbox(
                placeholder="What would you like to research?",
                show_label=False,
                container=False,
                autofocus=True,
                elem_id="dr-query",
                scale=1,
            )
            send_button = gr.Button("↑", variant="primary", elem_id="dr-send", scale=0, min_width=0)
        with gr.Column(elem_id="dr-examples-wrap") as examples_wrap:
            gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples", label=None)

    def blocked(error: QuotaError, resume) -> dict:
        """ Show a quota notice in place of the report, with the memory-only button when that run still fits """
        return {
            status: "",
            report: str(error),
            memory_button: gr.update(visible=error.memory_ok),
            resume_state: resume,
            usage_line: meter.summary_html(),
            topbar: current_topbar(),
        }

    async def ask(query: str, web_search: bool):
        """ Show the query as a message, then ask the clarifying questions """
        yield {
            query_state: query,
            web_search_state: web_search,
            query_textbox: "",
            home: gr.update(visible=False),
            examples_wrap: gr.update(visible=False),
            user_message: gr.update(value=query, visible=True),
            clarify_group: gr.update(visible=False),
            memory_button: gr.update(visible=False),
            status: status_html("Thinking of a few questions..."),
            report: "",
            usage_line: "",
        }
        try:
            questions = await ResearchManager().clarify(query, web_search)
        except QuotaError as e:
            yield blocked(e, None)
            return
        updates = {
            questions_state: questions,
            clarify_intro: CLARIFY_INTRO if web_search else MEMORY_INTRO,
            clarify_group: gr.update(visible=True),
            status: "",
            topbar: current_topbar(),
        }
        for i, (label, box, question) in enumerate(zip(question_labels, answer_boxes, questions), start=1):
            updates[label] = f"{i}. {question}"
            updates[box] = ""
        yield updates

    async def research(query: str, clarifications: list[tuple[str, str]], style: str, web_search: bool):
        """ Hide the questions and stream progress, then show the report """
        yield {clarify_group: gr.update(visible=False), memory_button: gr.update(visible=False), status: status_html("Starting research..."), report: "", usage_line: "", topbar: current_topbar()}
        previous = 0.0
        try:
            async for kind, update in ResearchManager().run(query, clarifications, style, web_search):
                if kind == "report":
                    yield {status: "", report: update, usage_line: meter.summary_html(MODEL_LINE), topbar: current_topbar()}
                else:
                    yield {status: progress_html(update, previous), topbar: current_topbar()}
                    previous = update.fraction
        except QuotaError as e:
            yield blocked(e, {"clarifications": clarifications, "style": style})

    async def clarify(query: str):
        """ A new query from the composer: always starts with web search on """
        query = query.strip()
        if query:
            async for update in ask(query, True):
                yield update

    async def run(query: str, web_search: bool, questions: list[str], style: str, *answers: str):
        async for update in research(query, list(zip(questions, answers)), style, web_search):
            yield update

    async def run_skip(query: str, web_search: bool, style: str):
        """ Run the research on the raw query, without clarifications """
        async for update in research(query, [], style, web_search):
            yield update

    async def continue_from_memory(query: str, resume):
        """ The quota stopped the research: redo the blocked step without web search """
        if resume is None:
            async for update in ask(query, False):
                yield update
        else:
            yield {web_search_state: False}
            async for update in research(query, resume["clarifications"], resume["style"], False):
                yield update

    outputs = [
        query_state, questions_state, web_search_state, resume_state, query_textbox, home, examples_wrap, user_message,
        clarify_group, clarify_intro, status, report, memory_button, usage_line, topbar,
    ] + question_labels + answer_boxes
    send_button.click(clarify, inputs=query_textbox, outputs=outputs, show_progress="hidden")
    query_textbox.submit(clarify, inputs=query_textbox, outputs=outputs, show_progress="hidden")
    start_button.click(run, inputs=[query_state, web_search_state, questions_state, citation_style] + answer_boxes, outputs=outputs, show_progress="hidden")
    skip_button.click(run_skip, inputs=[query_state, web_search_state, citation_style], outputs=outputs, show_progress="hidden")
    memory_button.click(continue_from_memory, inputs=[query_state, resume_state], outputs=outputs, show_progress="hidden")
    ui.load(current_topbar, outputs=topbar)


if __name__ == "__main__":
    ui.launch(css=CSS, js=JS, theme=gr.themes.Base(), auth=AUTH, auth_message=LOGIN_HTML)
