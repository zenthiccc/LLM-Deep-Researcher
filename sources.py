from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import asyncio
import json
import re
import httpx

FETCH_TIMEOUT = 6.0
MAX_HTML_BYTES = 400_000
MAX_CONCURRENT_FETCHES = 8
USER_AGENT = "Mozilla/5.0 (compatible; DeepResearch/1.0; +https://github.com)"


@dataclass
class Source:
    url: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    published: tuple[int, ...] | None = None  # (year,), (year, month) or (year, month, day)
    site_name: str = ""
    accessed: date = field(default_factory=date.today)
    id: int = 0


@dataclass
class SearchContext:
    """ Run context for one search: the search tool appends the sources it found """
    sources: list[Source] = field(default_factory=list)


@dataclass
class SearchResult:
    summary: str
    sources: list[Source]



def sources_from_annotations(items) -> list[Source]:
    """ Collect url_citation annotations from OpenAI's hosted web search results """
    found = []
    for item in items:
        for part in getattr(getattr(item, "raw_item", None), "content", None) or []:
            for annotation in getattr(part, "annotations", None) or []:
                if getattr(annotation, "type", "") == "url_citation" and annotation.url:
                    found.append(Source(url=annotation.url, title=annotation.title or ""))
    return found


# === Page metadata ===

class _MetaParser(HTMLParser):
    """ Collect <meta> values, the <title> text and JSON-LD blocks from a page's HTML """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.title = ""
        self.json_ld: list[str] = []
        self._in = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("itemprop") or "").lower()
            if key and a.get("content", "").strip():
                self.meta.setdefault(key, []).append(a["content"].strip())
        elif tag == "title" and not self.title:
            self._in = "title"
        elif tag == "script" and "ld+json" in a.get("type", ""):
            self._in = "json_ld"
            self.json_ld.append("")

    def handle_endtag(self, tag):
        if tag in ("title", "script"):
            self._in = None

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in == "json_ld":
            self.json_ld[-1] += data


def _json_ld_objects(blocks: list[str]):
    """ Yield every dict inside the page's JSON-LD blocks, including @graph entries """
    stack = []
    for block in blocks:
        try:
            stack.append(json.loads(block))
        except ValueError:
            continue
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            yield node
            stack.extend(v for k, v in node.items() if k == "@graph")


def _names(value) -> list[str]:
    """ Turn a JSON-LD author/publisher value into a list of names """
    if isinstance(value, list):
        return [n for v in value for n in _names(v)]
    if isinstance(value, dict):
        value = value.get("name", "")
    return [value.strip()] if isinstance(value, str) and value.strip() else []


def _clean_author(name: str) -> str:
    name = re.sub(r"^\s*by\s+", "", name, flags=re.I).strip()
    return "" if name.startswith("http") or "@" in name else name


def parse_date(value: str) -> tuple[int, ...] | None:
    """ Parse ISO, RFC 2822 or bare-year dates into (year, month, day) parts """
    value = (value or "").strip()
    m = re.match(r"^(\d{4})(?:[-/](\d{1,2})(?:[-/](\d{1,2}))?)?", value)
    if m:
        return tuple(int(p) for p in m.groups() if p)
    try:
        d = parsedate_to_datetime(value)
        return (d.year, d.month, d.day)
    except (TypeError, ValueError):
        pass
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            d = datetime.strptime(value, fmt)
            return (d.year, d.month, d.day)
        except ValueError:
            continue
    return None


def apply_metadata(source: Source, html: str) -> None:
    """ Fill in title, authors, date and site name from a page's HTML, keeping what's already known """
    parser = _MetaParser()
    try:
        parser.feed(html)
    except Exception:
        return
    meta = parser.meta
    first = lambda *keys: next((meta[k][0] for k in keys if k in meta), "")

    ld_title = ld_date = ld_site = ""
    ld_authors: list[str] = []
    for obj in _json_ld_objects(parser.json_ld):
        ld_title = ld_title or (obj.get("headline") or "")
        ld_date = ld_date or (obj.get("datePublished") or "")
        ld_authors = ld_authors or _names(obj.get("author"))
        ld_site = ld_site or next(iter(_names(obj.get("publisher"))), "")

    authors = meta.get("citation_author") or ld_authors or meta.get("author") or meta.get("article:author") or []
    authors = [a for a in (_clean_author(x) for x in authors) if a]
    if authors:
        source.authors = list(dict.fromkeys(authors))

    title = first("citation_title", "og:title", "twitter:title") or ld_title or parser.title.strip()
    if title:
        source.title = re.sub(r"\s+", " ", title)

    published = parse_date(first("citation_publication_date", "citation_date", "article:published_time", "datepublished", "date", "dc.date") or ld_date)
    if published:
        source.published = published

    site = first("og:site_name", "citation_journal_title", "application-name") or ld_site
    if site:
        source.site_name = site


def normalize_url(url: str) -> str:
    """ A key for spotting the same page: no scheme, www, fragment, trailing slash or tracking params """
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")])
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit(("", host, parts.path.rstrip("/"), query, ""))


def _domain(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _split_site_suffix(source: Source) -> None:
    """ "Solid-state battery - Wikipedia" -> title "Solid-state battery", site "Wikipedia" """
    parts = re.split(r"\s+[|\-–—·]\s+", source.title)
    if len(parts) < 2:
        return
    suffix = parts[-1].strip()
    key = re.sub(r"[^a-z0-9]", "", suffix.lower())
    if key and (key == re.sub(r"[^a-z0-9]", "", source.site_name.lower()) or key in _domain(source.url).replace(".", "")):
        source.title = re.split(r"\s+[|\-–—·]\s+" + re.escape(suffix) + r"$", source.title)[0].strip()
        if "." in source.site_name or not source.site_name:
            source.site_name = suffix


async def _enrich(client: httpx.AsyncClient, source: Source, limit: asyncio.Semaphore) -> None:
    """ Follow redirects to the real URL and read the page's metadata; on failure keep what we have """
    async with limit:
        try:
            async with client.stream("GET", source.url) as response:
                source.url = str(response.url)
                if response.status_code != 200 or "html" not in response.headers.get("content-type", ""):
                    return
                body = b""
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_HTML_BYTES or b"</head>" in body:
                        break
            apply_metadata(source, body.decode(response.encoding or "utf-8", errors="replace"))
        except (httpx.HTTPError, UnicodeError, LookupError):
            return


async def gather_sources(results: list[SearchResult]) -> list[Source]:
    """ Resolve and enrich every source, merge duplicates and number them in order of first appearance """
    raw = [s for r in results for s in r.sources]
    if not raw:
        return []
    limit = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(follow_redirects=True, timeout=FETCH_TIMEOUT, headers=headers) as client:
        await asyncio.gather(*(_enrich(client, s, limit) for s in raw))

    unique: dict[str, Source] = {}
    for source in raw:
        source.site_name = source.site_name or _domain(source.url)
        source.title = source.title or source.url
        _split_site_suffix(source)
        key = normalize_url(source.url)
        if key in unique:
            source.id = unique[key].id
        else:
            source.id = len(unique) + 1
            unique[key] = source
    return list(unique.values())
