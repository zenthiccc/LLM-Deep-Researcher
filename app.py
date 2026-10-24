import html
import re
import gradio as gr
from dotenv import load_dotenv
from research_manager import Progress, ResearchManager
from clarifier_agent import NUM_QUESTIONS
from usage import QuotaError, meter
from styles import CSS, JS, EXAMPLES, topbar_html, GREETING_HTML, ASSISTANT_LABEL_HTML

load_dotenv(override=True)


def status_html(text: str) -> str:
    """ Render a progress line with a pulsing dot, keeping any URL clickable """
    body = re.sub(r"(https?://\S+)", r'<a href="\1" target="_blank">trace</a>', html.escape(text))
    return f'<div class="dr-status"><span class="dr-dot"></span>{body}</div>'


CHECK_SVG = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'


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


def current_topbar() -> str:
    return topbar_html(meter.compact_html())


with gr.Blocks(title="Deep Research") as ui:
    query_state = gr.State("")
    questions_state = gr.State([])

    topbar = gr.HTML(current_topbar())

    with gr.Column(elem_id="dr-thread"):
        with gr.Column(elem_id="dr-home") as home:
            gr.HTML(GREETING_HTML)

        user_message = gr.Markdown(visible=False, elem_id="dr-user-msg")

        with gr.Group(visible=False, elem_id="dr-clarify") as clarify_group:
            gr.HTML(ASSISTANT_LABEL_HTML + '<p class="dr-clarify-intro">A few quick questions so I can focus the research. Answer any you like.</p>')
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

    async def clarify(query: str):
        """ Show the query as a message, then ask the clarifying questions """
        query = query.strip()
        if not query:
            return
        yield {
            query_state: query,
            query_textbox: "",
            home: gr.update(visible=False),
            examples_wrap: gr.update(visible=False),
            user_message: gr.update(value=query, visible=True),
            clarify_group: gr.update(visible=False),
            status: status_html("Thinking of a few questions..."),
            report: "",
            usage_line: "",
        }
        try:
            questions = await ResearchManager().clarify(query)
        except QuotaError as e:
            yield {status: "", report: str(e), usage_line: meter.summary_html(), topbar: current_topbar()}
            return
        updates = {questions_state: questions, clarify_group: gr.update(visible=True), status: "", topbar: current_topbar()}
        for i, (label, box, question) in enumerate(zip(question_labels, answer_boxes, questions), start=1):
            updates[label] = f"{i}. {question}"
            updates[box] = ""
        yield updates

    async def run(query: str, questions: list[str], style: str, *answers: str):
        """ Hide the questions and stream progress, then show the report """
        clarifications = list(zip(questions, answers))
        yield gr.update(visible=False), status_html("Starting research..."), "", "", current_topbar()
        previous = 0.0
        async for kind, update in ResearchManager().run(query, clarifications, style):
            if kind == "report":
                yield gr.update(visible=False), "", update, meter.summary_html(), current_topbar()
            else:
                yield gr.update(visible=False), progress_html(update, previous), "", "", current_topbar()
                previous = update.fraction

    async def run_skip(query: str, style: str):
        """ Run the research on the raw query, without clarifications """
        async for update in run(query, [], style):
            yield update

    clarify_outputs = [query_state, query_textbox, home, examples_wrap, user_message, clarify_group, status, report, usage_line, topbar, questions_state] + question_labels + answer_boxes
    run_outputs = [clarify_group, status, report, usage_line, topbar]
    send_button.click(clarify, inputs=query_textbox, outputs=clarify_outputs, show_progress="hidden")
    query_textbox.submit(clarify, inputs=query_textbox, outputs=clarify_outputs, show_progress="hidden")
    start_button.click(run, inputs=[query_state, questions_state, citation_style] + answer_boxes, outputs=run_outputs, show_progress="hidden")
    skip_button.click(run_skip, inputs=[query_state, citation_style], outputs=run_outputs, show_progress="hidden")
    ui.load(current_topbar, outputs=topbar)


if __name__ == "__main__":
    ui.launch(css=CSS, js=JS, theme=gr.themes.Base())
