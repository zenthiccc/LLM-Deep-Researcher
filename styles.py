EXAMPLES = [
    "Most popular AI Agent frameworks in 2026",
    "Top universities in the world",
    "Most popular TV series ever",
]

MARK_HTML = """
<span class="dr-mark">
    <span class="dr-bar dr-bar-1"></span>
    <span class="dr-bar dr-bar-2"></span>
    <span class="dr-bar dr-bar-3"></span>
</span>
"""

def topbar_html(usage: str = "") -> str:
    """ The top bar, with the usage counter (if any) on the right """
    return f'<div class="dr-topbar">{MARK_HTML}<span class="dr-topbar-name">Deep Research</span>{usage}</div>'

GREETING_HTML = f"""
<div class="dr-greeting">
    <div class="dr-greeting-mark">{MARK_HTML}</div>
    <h1>What should we research today?</h1>
    <p>Ask a question. I'll ask a few of my own, search the web, and write you a report.</p>
</div>
"""

ASSISTANT_LABEL_HTML = f'<div class="dr-assistant-label">{MARK_HTML}<span>Deep Research</span></div>'

CSS = """
:root {
    --dr-bg: #faf9f5;
    --dr-surface: #ffffff;
    --dr-bubble: #f0eee6;
    --dr-line: #e5e3da;
    --dr-line-strong: #d6d3c8;
    --dr-text: #1f1e1d;
    --dr-muted: #73726c;
    --dr-accent: #c96442;
    --dr-accent-hover: #b5573a;
    --dr-accent-soft: #e8b49e;
    --dr-sand: #d4a27f;
    --dr-shadow: 0 0.25rem 1.25rem rgba(31, 30, 29, 0.06), 0 0 0 0.5px rgba(31, 30, 29, 0.08);
    --dr-sans: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --dr-serif: ui-serif, "Iowan Old Style", Georgia, Cambria, "Times New Roman", serif;
}

.gradio-container {
    box-sizing: border-box !important;
    width: 100% !important;
    max-width: 780px !important;
    margin: 0 auto !important;
    padding: 1rem 1.25rem 0 !important;
    background: var(--dr-bg) !important;
    color: var(--dr-text) !important;
    font-family: var(--dr-sans) !important;
    min-height: 100vh;
    display: flex !important;
    flex-direction: column !important;
}

.dark {
    --dr-bg: #262624;
    --dr-surface: #30302e;
    --dr-bubble: #141413;
    --dr-line: #3e3d39;
    --dr-line-strong: #4f4d47;
    --dr-text: #f5f4ef;
    --dr-muted: #a6a39a;
    --dr-accent: #d97757;
    --dr-accent-hover: #c96442;
    --dr-accent-soft: #7a4a38;
    --dr-shadow: 0 0.25rem 1.25rem rgba(0, 0, 0, 0.25), 0 0 0 0.5px rgba(255, 255, 255, 0.08);
}

body, gradio-app { background: var(--dr-bg) !important; }

.gradio-container .block, .gradio-container .form, .gradio-container .gap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

footer { display: none !important; }
.gradio-container > .main { padding-left: 0 !important; padding-right: 0 !important; }

/* === MARK === */
.dr-mark { display: inline-flex; flex-direction: column; gap: 3px; width: 18px; flex: none; }
.dr-bar { height: 4px; border-radius: 2px; display: block; }
.dr-bar-1 { background: var(--dr-accent); width: 100%; }
.dr-bar-2 { background: var(--dr-sand);   width: 72%;  }
.dr-bar-3 { background: var(--dr-accent-soft); width: 46%; }

/* === TOP BAR === */
.dr-topbar {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.25rem 0 0.5rem;
    font-family: var(--dr-serif);
    font-size: 1.05rem;
    color: var(--dr-text);
}
.dr-topbar-name { white-space: nowrap; }
.dr-usage {
    margin-left: auto;
    padding: 0.2rem 0.65rem;
    border: 1px solid var(--dr-line);
    border-radius: 999px;
    font-family: var(--dr-sans);
    font-size: 0.8rem;
    color: var(--dr-muted);
    white-space: nowrap;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: default;
}
.dr-usage-warn { color: var(--dr-accent); border-color: var(--dr-accent-soft); }

/* === THREAD === */
#dr-thread { gap: 1.25rem !important; padding-bottom: 1rem; }

/* Once the greeting is gone, pin the composer to the bottom of the window like a chat */
.gradio-container:not(:has(#dr-home)) #dr-thread { padding-bottom: 7rem; }
.gradio-container:not(:has(#dr-home)) #dr-composer-wrap {
    position: fixed !important;
    left: 50%;
    transform: translateX(-50%);
    width: min(780px, 100vw) !important;
    box-sizing: border-box;
    padding: 0.75rem 1.25rem 1.25rem !important;
}

.dr-greeting { text-align: center; padding: 18vh 0 1.5rem; }
.dr-greeting-mark .dr-mark { width: 34px; gap: 5px; }
.dr-greeting-mark .dr-bar { height: 7px; border-radius: 4px; }
.dr-greeting h1 {
    font-family: var(--dr-serif);
    font-weight: 400;
    font-size: clamp(1.75rem, 4vw, 2.35rem);
    letter-spacing: -0.01em;
    color: var(--dr-text);
    margin: 1rem 0 0.5rem;
}
.dr-greeting p { color: var(--dr-muted); font-size: 0.95rem; margin: 0; }

/* User message: right-aligned bubble */
#dr-user-msg {
    align-self: flex-end;
    max-width: 85%;
    width: fit-content !important;
    background: var(--dr-bubble) !important;
    border-radius: 1rem !important;
    padding: 0.65rem 1rem !important;
    margin-top: 1.5rem;
}
#dr-user-msg, #dr-user-msg * { color: var(--dr-text) !important; font-size: 0.98rem; }
#dr-user-msg p { margin: 0; line-height: 1.5; }

.dr-assistant-label {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--dr-muted);
    margin-bottom: 0.5rem;
}

/* === CLARIFY (assistant message) === */
#dr-clarify, #dr-clarify .styler {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    gap: 0.35rem !important;
}

.dr-clarify-intro, .dr-clarify-intro * {
    font-family: var(--dr-serif) !important;
    font-size: 1.05rem !important;
    line-height: 1.6 !important;
    color: var(--dr-text) !important;
}
.dr-clarify-intro { padding: 0 !important; margin: 0 0 0.5rem !important; }
.dr-clarify-intro p { margin: 0 !important; }

.dr-question, .dr-question * {
    font-family: var(--dr-serif) !important;
    font-size: 1.02rem !important;
    color: var(--dr-text) !important;
}
.dr-question { margin-top: 0.6rem !important; padding: 0 !important; }

.dr-answer textarea, .dr-answer input {
    background: var(--dr-surface) !important;
    color: var(--dr-text) !important;
    border: 1px solid var(--dr-line) !important;
    border-radius: 0.75rem !important;
    padding: 0.65rem 0.9rem !important;
    font-size: 0.95rem !important;
    box-shadow: none !important;
    transition: border-color 0.15s !important;
}
.dr-answer textarea:focus, .dr-answer input:focus {
    outline: none !important;
    border-color: var(--dr-line-strong) !important;
}

.dr-clarify-actions { gap: 0.5rem !important; margin-top: 0.85rem !important; justify-content: flex-start !important; }

#dr-start, #dr-skip {
    border-radius: 0.6rem !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1rem !important;
    box-shadow: none !important;
    min-width: 0 !important;
    width: auto !important;
    flex: none !important;
    white-space: nowrap !important;
    transition: background 0.15s, border-color 0.15s !important;
}
#dr-start { background: var(--dr-accent) !important; color: #ffffff !important; border: 1px solid var(--dr-accent) !important; }
#dr-start:hover { background: var(--dr-accent-hover) !important; border-color: var(--dr-accent-hover) !important; }
#dr-skip { background: transparent !important; color: var(--dr-text) !important; border: 1px solid var(--dr-line-strong) !important; }
#dr-skip:hover { background: var(--dr-bubble) !important; }

/* Citation style: a small segmented control at the end of the actions row */
.dr-clarify-actions > .form:has(#dr-style) {
    margin-left: auto !important;
    flex: none !important;
    width: auto !important;
    min-width: 0 !important;
    overflow: visible !important;
    background: transparent !important;
    border: none !important;
}
#dr-style {
    display: flex !important;
    align-items: center !important;
    gap: 0.6rem !important;
    width: auto !important;
    min-width: 0 !important;
    flex: none !important;
    overflow: visible !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
}
#dr-style > span, #dr-style .block-title, #dr-style [data-testid="block-info"] {
    font-size: 0.82rem !important;
    color: var(--dr-muted) !important;
    background: transparent !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}
#dr-style > .wrap:not([data-testid="status-tracker"]) { display: inline-flex !important; gap: 0 !important; border: 1px solid var(--dr-line-strong) !important; border-radius: 0.6rem !important; overflow: hidden; padding: 0 !important; }
#dr-style label {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0.4rem 0.8rem !important;
    margin: 0 !important;
    font-size: 0.85rem !important;
    color: var(--dr-muted) !important;
    white-space: nowrap;
    cursor: pointer;
}
#dr-style label + label { border-left: 1px solid var(--dr-line-strong) !important; }
#dr-style label.selected, #dr-style label:has(input:checked) { background: var(--dr-bubble) !important; color: var(--dr-text) !important; font-weight: 600; }
#dr-style input[type="radio"] { display: none !important; }

/* === STATUS === */
.dr-status {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    color: var(--dr-muted);
    font-size: 0.92rem;
}
.dr-status a { color: var(--dr-muted); text-decoration: underline; text-underline-offset: 2px; }
.dr-dot {
    width: 0.6rem;
    height: 0.6rem;
    border-radius: 50%;
    background: var(--dr-accent);
    animation: dr-pulse 1.2s ease-in-out infinite;
    flex: none;
}
@keyframes dr-pulse {
    0%, 100% { opacity: 0.35; transform: scale(0.85); }
    50% { opacity: 1; transform: scale(1); }
}

/* === PROGRESS (card shown while a report is made) === */
#dr-status-wrap .html-container { padding: 0 !important; }
.dr-progress {
    background: var(--dr-surface);
    border: 1px solid var(--dr-line);
    border-radius: 0.9rem;
    box-shadow: var(--dr-shadow);
    padding: 1rem 1.1rem 0.9rem;
    font-family: var(--dr-sans);
}
.dr-progress-bar {
    position: relative;
    height: 4px;
    border-radius: 2px;
    background: var(--dr-line);
    overflow: hidden;
    margin-bottom: 0.9rem;
}
.dr-progress-bar span {
    position: absolute;
    inset: 0 auto 0 0;
    width: var(--to);
    border-radius: 2px;
    background: linear-gradient(90deg, var(--dr-sand), var(--dr-accent));
    animation: dr-fill 0.6s ease-out;
    overflow: hidden;
}
/* A sheen moving along the filled part, so the bar looks alive while a step takes a while */
.dr-progress-bar span::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
    transform: translateX(-100%);
    animation: dr-sheen 1.6s ease-in-out infinite;
}
@keyframes dr-fill { from { width: var(--from); } to { width: var(--to); } }
@keyframes dr-sheen { to { transform: translateX(100%); } }

.dr-steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.55rem; }
.dr-step {
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    font-size: 0.92rem;
    line-height: 1.4;
    color: var(--dr-muted);
    margin: 0 !important;
}
.dr-step-active { color: var(--dr-text); font-weight: 500; }
.dr-step-icon {
    flex: none;
    box-sizing: border-box;
    width: 1.1rem;
    height: 1.1rem;
    margin-top: 0.05rem;
    border-radius: 50%;
    border: 1.5px solid var(--dr-line-strong);
    display: inline-flex;
    align-items: center;
    justify-content: center;
}
.dr-step-done .dr-step-icon { border: none; background: var(--dr-accent); color: #ffffff; }
.dr-step-done .dr-step-icon svg { width: 0.7rem; height: 0.7rem; }
.dr-step-active .dr-step-icon { border-color: var(--dr-accent); }
.dr-step-active .dr-step-icon::after {
    content: "";
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: var(--dr-accent);
    animation: dr-pulse 1.2s ease-in-out infinite;
}
.dr-progress-trace {
    display: inline-block;
    margin-top: 0.75rem;
    font-size: 0.82rem;
    color: var(--dr-muted) !important;
    text-decoration: underline;
    text-underline-offset: 2px;
}

/* "Continue without web search" under a quota notice */
#dr-memory {
    align-self: flex-start;
    width: auto !important;
    min-width: 0 !important;
    border-radius: 0.6rem !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1rem !important;
    background: var(--dr-accent) !important;
    color: #ffffff !important;
    border: 1px solid var(--dr-accent) !important;
    box-shadow: none !important;
    transition: background 0.15s !important;
}
#dr-memory:hover { background: var(--dr-accent-hover) !important; border-color: var(--dr-accent-hover) !important; }

@media (prefers-reduced-motion: reduce) {
    .dr-progress-bar span, .dr-progress-bar span::after, .dr-dot, .dr-step-active .dr-step-icon::after { animation: none; }
}

/* === USAGE LINE (under the report) === */
.dr-usage-line {
    margin-top: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--dr-line);
    font-family: var(--dr-sans);
    font-size: 0.82rem;
    line-height: 1.6;
    color: var(--dr-muted);
}
#dr-usage-wrap .html-container { padding: 0 !important; }
.dr-usage-line, .dr-usage-line * { color: var(--dr-muted) !important; }
.dr-usage-line span { opacity: 0.8; }

/* === REPORT (assistant message, serif reading text) === */
#dr-report, #dr-report .prose {
    background: transparent !important;
    color: var(--dr-text) !important;
    font-family: var(--dr-serif) !important;
    font-size: 1.05rem;
}
#dr-report p, #dr-report li { line-height: 1.7; }
#dr-report h1, #dr-report h2, #dr-report h3 {
    font-family: var(--dr-serif) !important;
    color: var(--dr-text) !important;
    font-weight: 600;
    letter-spacing: -0.01em;
    border: none !important;
}
#dr-report h1 { font-size: 1.6rem; margin: 0.5rem 0 1rem; }
#dr-report h2 { font-size: 1.3rem; margin-top: 1.75rem; }
#dr-report h3 { font-size: 1.1rem; margin-top: 1.4rem; }
#dr-report a { color: var(--dr-accent); text-decoration: underline; text-underline-offset: 3px; }
#dr-report code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    background: var(--dr-bubble);
    border-radius: 0.3rem;
    padding: 0.1rem 0.35rem;
    font-size: 0.88em;
}
#dr-report pre {
    background: var(--dr-bubble);
    border: 1px solid var(--dr-line);
    border-radius: 0.6rem;
    padding: 0.9rem 1.1rem;
}
#dr-report blockquote {
    border-left: 3px solid var(--dr-line-strong) !important;
    margin: 1rem 0;
    padding: 0.1rem 1rem;
    color: var(--dr-muted);
}
#dr-report ul, #dr-report ol { padding-left: 1.4rem; }
#dr-report table { border-collapse: collapse; font-family: var(--dr-sans); font-size: 0.92rem; }
#dr-report th, #dr-report td { border: 1px solid var(--dr-line); padding: 0.45rem 0.75rem; text-align: left; }
#dr-report th { background: var(--dr-bubble); font-weight: 600; }

/* === COMPOSER === */
#dr-composer-wrap {
    bottom: 0;
    z-index: 10;
    padding: 0.75rem 0 1.25rem !important;
    background: linear-gradient(to bottom, transparent, var(--dr-bg) 30%) !important;
}

#dr-composer {
    background: var(--dr-surface) !important;
    border: 1px solid var(--dr-line) !important;
    border-radius: 1.25rem !important;
    box-shadow: var(--dr-shadow) !important;
    padding: 0.55rem 0.55rem 0.55rem 0.4rem !important;
    align-items: flex-end !important;
    gap: 0.5rem !important;
    flex-wrap: nowrap !important;
    transition: border-color 0.15s !important;
}
#dr-composer:focus-within { border-color: var(--dr-line-strong) !important; }

#dr-query textarea, #dr-query input {
    background: transparent !important;
    color: var(--dr-text) !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0.55rem 0.6rem !important;
    font-size: 1rem !important;
    font-family: var(--dr-sans) !important;
    line-height: 1.5 !important;
    resize: none !important;
}
#dr-query textarea:focus, #dr-query input:focus { outline: none !important; box-shadow: none !important; }
#dr-query textarea::placeholder, #dr-query input::placeholder { color: var(--dr-muted) !important; opacity: 1 !important; }

#dr-send {
    width: 2.25rem !important;
    height: 2.25rem !important;
    min-width: 2.25rem !important;
    max-width: 2.25rem !important;
    padding: 0 !important;
    border-radius: 0.6rem !important;
    background: var(--dr-accent) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    flex: none !important;
    transition: background 0.15s !important;
}
#dr-send:hover { background: var(--dr-accent-hover) !important; }

/* === EXAMPLES (suggestion chips) === */
#dr-examples-wrap { margin-top: 0.85rem !important; }

#dr-examples > .label { display: none !important; }
#dr-examples { background: transparent !important; border: none !important; }
#dr-examples > .gallery {
    display: flex !important;
    flex-wrap: wrap !important;
    justify-content: center !important;
    gap: 0.5rem !important;
}

#dr-examples .gallery-item {
    background: transparent !important;
    border: 1px solid var(--dr-line) !important;
    border-radius: 0.6rem !important;
    padding: 0.45rem 0.85rem !important;
    font-size: 0.88rem !important;
    color: var(--dr-muted) !important;
    cursor: pointer !important;
    margin: 0 !important;
    box-shadow: none !important;
    transition: background 0.15s, color 0.15s, border-color 0.15s !important;
}
#dr-examples .gallery-item:hover {
    background: var(--dr-surface) !important;
    color: var(--dr-text) !important;
    border-color: var(--dr-line-strong) !important;
}

@media (max-width: 700px) {
    .gradio-container { padding: 0.75rem 1rem 0 !important; }
    .gradio-container:not(:has(#dr-home)) #dr-composer-wrap { padding: 0.5rem 1rem 1rem !important; }
    .dr-greeting { padding-top: 10vh; }
    #dr-user-msg { max-width: 92%; }
}
"""

JS = """
() => {
    const focus = () => {
        const el = document.querySelector("#dr-query textarea, #dr-query input");
        if (el) { el.focus(); return true; }
        return false;
    };
    if (!focus()) {
        let tries = 0;
        const i = setInterval(() => {
            if (focus() || ++tries > 20) clearInterval(i);
        }, 100);
    }
}
"""
