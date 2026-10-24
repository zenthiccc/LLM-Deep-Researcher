import gradio as gr
from dotenv import load_dotenv
from research_manager import ResearchManager
from clarifier_agent import NUM_QUESTIONS
from styles import CSS, JS, EXAMPLES, HEADER_HTML

load_dotenv(override=True)


async def clarify(query: str):
    """ Generate clarifying questions and reveal the clarification panel """
    if not query.strip():
        return [[], gr.update(visible=False), ""] + [gr.update()] * (2 * NUM_QUESTIONS)
    questions = await ResearchManager().clarify(query)
    labels = [gr.update(value=f"**{i + 1}. {q}**") for i, q in enumerate(questions)]
    answers = [gr.update(value="") for _ in questions]
    return [questions, gr.update(visible=True), ""] + labels + answers


async def run(query: str, questions: list[str], *answers: str):
    """ Hide the clarification panel and stream the research, using any answers given """
    clarifications = list(zip(questions, answers))
    yield gr.update(visible=False), "Starting research..."
    async for status_update in ResearchManager().run(query, clarifications):
        yield gr.update(visible=False), status_update


async def run_skip(query: str):
    """ Run the research on the raw query, without clarifications """
    async for update in run(query, []):
        yield update


with gr.Blocks(title="Deep Research") as ui:
    gr.HTML(HEADER_HTML)
    questions_state = gr.State([])

    with gr.Row(elem_classes="dr-query-row"):
        query_textbox = gr.Textbox(
            placeholder="Type a research question...",
            show_label=False,
            container=False,
            autofocus=True,
            elem_id="dr-query",
            scale=5,
        )
        run_button = gr.Button("Investigate", variant="primary", elem_id="dr-run", scale=1)

    with gr.Group(visible=False, elem_id="dr-clarify") as clarify_group:
        gr.HTML('<div class="dr-clarify-label">A few questions first</div>')
        question_labels, answer_boxes = [], []
        for i in range(NUM_QUESTIONS):
            question_labels.append(gr.Markdown(elem_classes="dr-question"))
            answer_boxes.append(gr.Textbox(show_label=False, placeholder="Your answer (optional)", elem_classes="dr-answer"))
        with gr.Row(elem_classes="dr-clarify-actions"):
            start_button = gr.Button("Start research", variant="primary", elem_id="dr-start")
            skip_button = gr.Button("Skip clarifications", variant="secondary", elem_id="dr-skip")

    gr.HTML('<div class="dr-examples-label">Try one</div>')
    gr.Examples(examples=EXAMPLES, inputs=query_textbox, elem_id="dr-examples")

    report = gr.Markdown(elem_id="dr-report")

    clarify_outputs = [questions_state, clarify_group, report] + question_labels + answer_boxes
    run_button.click(clarify, inputs=query_textbox, outputs=clarify_outputs)
    query_textbox.submit(clarify, inputs=query_textbox, outputs=clarify_outputs)
    start_button.click(run, inputs=[query_textbox, questions_state] + answer_boxes, outputs=[clarify_group, report])
    skip_button.click(run_skip, inputs=query_textbox, outputs=[clarify_group, report])


if __name__ == "__main__":
    ui.launch(css=CSS, js=JS, theme=gr.themes.Base())
