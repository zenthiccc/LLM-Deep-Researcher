"""
Link previews: the title, description and image that chat apps and social sites show for a shared link.
Crawlers don't run JavaScript or sign in, and behind the login Gradio leaves its meta tags empty (after its
own "Gradio" defaults), so a middleware puts ours into the page's HTML and serves the image before the
login check.
"""
from pathlib import Path
from starlette.middleware import Middleware
from starlette.responses import FileResponse
import html
import os
import re

ASSETS = Path(__file__).with_name("assets")
PREVIEW_IMAGE = ASSETS / "preview.png"
FAVICON = ASSETS / "favicon.png"

TITLE = "Deep Research"
DESCRIPTION = "Ask a question, answer a few of mine, and get a long report built from web sources, with IEEE or APA references."
IMAGE_ALT = "The Deep Research logo above the words: Ask a question and get a report built from web sources."

PUBLIC_FILES = {"/preview.png": PREVIEW_IMAGE, "/apple-touch-icon.png": FAVICON}

# Gradio's own tags: its "Gradio" defaults, the ones it fills from the config, and the page title
OLD_TAGS = re.compile(r'<meta\s+(?:property="og:|name="twitter:|name="description")[^>]*>\s*|<title>.*?</title>\s*', re.S)


def base_url(scope: dict) -> str:
    """ The public URL of the app: PUBLIC_URL, Render's own URL, or the request's host """
    url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if url:
        return url.rstrip("/")
    headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
    scheme = headers.get("x-forwarded-proto", scope.get("scheme", "http")).split(",")[0].strip()
    return f"{scheme}://{headers.get('host', 'localhost')}"


def meta_tags(url: str) -> str:
    title, description, alt = (html.escape(t, quote=True) for t in (TITLE, DESCRIPTION, IMAGE_ALT))
    image = html.escape(f"{url}/preview.png", quote=True)
    page = html.escape(f"{url}/", quote=True)
    return f"""<title>{title}</title>
<meta name="description" content="{description}" />
<meta name="theme-color" content="#faf9f5" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#262624" media="(prefers-color-scheme: dark)" />
<link rel="apple-touch-icon" href="{html.escape(url, quote=True)}/apple-touch-icon.png" />
<meta property="og:type" content="website" />
<meta property="og:site_name" content="{title}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{description}" />
<meta property="og:url" content="{page}" />
<meta property="og:image" content="{image}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:image:alt" content="{alt}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{description}" />
<meta name="twitter:image" content="{image}" />
<meta name="twitter:image:alt" content="{alt}" />
"""


def add_meta_tags(page: str, url: str) -> str:
    """ Replace Gradio's meta tags and title with ours, right after the charset """
    page = OLD_TAGS.sub("", page)
    charset = re.search(r"<meta charset[^>]*>", page)
    at = charset.end() if charset else page.find("<head>") + len("<head>")
    return page[:at] + "\n" + meta_tags(url) + page[at:]


class LinkPreviewMiddleware:
    """ ASGI middleware: serves the preview files publicly and adds the meta tags to the page at / """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            return await self.app(scope, receive, send)
        if scope["path"] in PUBLIC_FILES:
            response = FileResponse(PUBLIC_FILES[scope["path"]], headers={"Cache-Control": "public, max-age=86400"})
            return await response(scope, receive, send)
        if scope["path"] != "/" or scope["method"] != "GET":
            return await self.app(scope, receive, send)

        start, chunks = None, []

        async def rewrite(message):
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
                return
            if message["type"] != "http.response.body":
                return await send(message)
            chunks.append(message.get("body", b""))
            if message.get("more_body"):
                return
            body = b"".join(chunks)
            headers = {k.lower(): v for k, v in start["headers"]}
            if start["status"] == 200 and headers.get(b"content-type", b"").startswith(b"text/html") and b"content-encoding" not in headers:
                body = add_meta_tags(body.decode(), base_url(scope)).encode()
            start_headers = [(k, v) for k, v in start["headers"] if k.lower() != b"content-length"]
            start_headers.append((b"content-length", str(len(body)).encode()))
            await send({**start, "headers": start_headers})
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, rewrite)


MIDDLEWARE = [Middleware(LinkPreviewMiddleware)]
