import re
from urllib.parse import quote
from sources import Source

STYLES = ("ieee", "apa")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
IEEE_MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
GROUP_WORDS = {"staff", "team", "news", "editor", "editors", "editorial", "board", "inc", "inc.", "ltd", "llc", "university",
               "press", "institute", "agency", "association", "department", "ministry", "foundation", "reuters", "desk"}

# One or more adjacent markers like [3], [1, 4], [2-5] or [1][3], but not markdown links like [1](url)
MARKER_RUN = re.compile(r"([ \t]*)(\[\d+(?:\s*[-–,]\s*\d+)*\](?!\()(?:[ \t]*\[\d+(?:\s*[-–,]\s*\d+)*\](?!\())*)")
REFERENCES_HEADING = re.compile(r"^(#{1,6})\s*(references|sources|bibliography|works cited)\s*:?\s*$", re.I | re.M)


# === Names ===

def _is_group(name: str) -> bool:
    words = name.replace(",", " ").split()
    return len(words) == 1 or len(words) > 4 or any(w.lower() in GROUP_WORDS for w in words)


def _split_name(name: str) -> tuple[str, list[str]] | None:
    """ (surname, given names) for a person, or None for an organization """
    name = re.sub(r"^(?:(?:dr|prof|mr|mrs|ms|sir)\.?\s+)+", "", name.strip(), flags=re.I)
    if _is_group(name):
        return None
    if "," in name:
        surname, given = name.split(",", 1)
        return surname.strip(), given.split()
    *given, surname = name.split()
    return surname, given


def _initials(given: list[str]) -> str:
    """ "Jean-Paul A." -> "J.-P. A." """
    return " ".join("-".join(part[0].upper() + "." for part in g.split("-") if part) for g in given)


def _apa_author(name: str) -> str:
    split = _split_name(name)
    if not split:
        return name
    surname, given = split
    return f"{surname}, {_initials(given)}" if given else surname


def _ieee_author(name: str) -> str:
    split = _split_name(name)
    if not split:
        return name
    surname, given = split
    return f"{_initials(given)} {surname}".strip()


def _surname(name: str) -> str:
    split = _split_name(name)
    return split[0] if split else name


# === Text helpers ===

def _md(text: str) -> str:
    """ Escape characters that would turn into markdown formatting """
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", text)


def _url(url: str) -> str:
    return f"<{quote(url, safe=':/?#[]@!$&\'()*+,;=%~-._')}>"


def _end(text: str) -> str:
    """ Add a period unless the text already ends with punctuation """
    return text if text.endswith((".", "?", "!")) else text + "."


def _is_domain(name: str) -> bool:
    return bool(re.fullmatch(r"[\w.-]+\.[a-z]{2,}", name.lower()))


def _year(source: Source) -> str:
    return str(source.published[0]) if source.published else "n.d."


# === APA 7 ===

def _apa_group_author(source: Source) -> str:
    """ With no named authors, APA uses the organization; a bare domain doesn't count """
    return "" if source.authors or _is_domain(source.site_name) else source.site_name


def _apa_authors(source: Source) -> str:
    if not source.authors:
        return _apa_group_author(source)
    names = [_apa_author(a) for a in source.authors]
    if len(names) == 1:
        return names[0]
    if len(names) > 20:
        return ", ".join(names[:19]) + ", . . . " + names[-1]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def _apa_date(source: Source) -> str:
    if not source.published:
        return "n.d."
    parts = source.published
    if len(parts) == 1:
        return str(parts[0])
    text = f"{parts[0]}, {MONTHS[parts[1] - 1]}"
    return f"{text} {parts[2]}" if len(parts) == 3 else text


def apa_entry(source: Source) -> str:
    author = _apa_authors(source)
    title = _md(source.title.rstrip("."))
    title = f"*{title}*" if title.endswith(("?", "!")) else f"*{title}*."
    site = "" if author == source.site_name else f" {_md(_end(source.site_name))}"
    if author:
        return f"{_end(_md(author))} ({_apa_date(source)}). {title}{site} {_url(source.url)}"
    return f"{title} ({_apa_date(source)}).{site} {_url(source.url)}"


def apa_label(source: Source) -> str:
    """ The author part of an APA in-text citation """
    if source.authors:
        names = [_surname(a) for a in source.authors]
        if len(names) == 1:
            return _md(names[0])
        if len(names) == 2:
            return _md(f"{names[0]} & {names[1]}")
        return _md(names[0]) + " et al."
    group = _apa_group_author(source)
    if group:
        return _md(group)
    words = source.title.split()
    short = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
    return f"*{_md(short)}*"


def _apa_sort_key(source: Source) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (_apa_authors(source) or source.title).lower())


def _apa_years(sources: list[Source]) -> dict[int, str]:
    """ Years for in-text citations, with a/b suffixes when the same author has several works in one year """
    groups: dict[tuple[str, str], list[Source]] = {}
    for s in sources:
        groups.setdefault((apa_label(s), _year(s)), []).append(s)
    years = {}
    for (_, year), group in groups.items():
        group.sort(key=lambda s: s.title.lower())
        for i, s in enumerate(group):
            suffix = "" if len(group) == 1 else ("-" if year == "n.d." else "") + "abcdefghijklmnopqrstuvwxyz"[i % 26]
            years[s.id] = year + suffix
    return years


# === IEEE ===

def _ieee_authors(source: Source) -> str:
    names = [_ieee_author(a) for a in source.authors]
    if len(names) > 6:
        return names[0] + " et al."
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def _ieee_date(parts: tuple[int, ...]) -> str:
    if len(parts) == 1:
        return str(parts[0])
    month = IEEE_MONTHS[parts[1] - 1]
    return f"{month} {parts[2]}, {parts[0]}" if len(parts) == 3 else f"{month} {parts[0]}"


def ieee_entry(source: Source, number: int) -> str:
    authors = _ieee_authors(source)
    head = f"{_md(authors)}, " if authors else ""
    title = _md(source.title.rstrip("."))
    title = f'"{title}"' if title.endswith(("?", "!")) else f'"{title},"'
    site = _md(source.site_name)
    published = f", {_ieee_date(source.published)}" if source.published else ""
    accessed = _ieee_date((source.accessed.year, source.accessed.month, source.accessed.day))
    return f"\\[{number}\\] {head}{title} {site}{published}. Accessed: {accessed}. \\[Online\\]. Available: {_url(source.url)}"


# === Applying citations to a report ===

def _marker_ids(run: str) -> list[int]:
    ids = []
    for a, b in re.findall(r"(\d+)(?:\s*[-–]\s*(\d+))?", run):
        start, end = int(a), int(b or a)
        ids.extend(range(start, end + 1) if 0 < end - start < 50 else [start])
    return ids


def strip_references_section(markdown: str) -> str:
    """ Remove any references section the writer added, since one is generated from real source data """
    match = REFERENCES_HEADING.search(markdown)
    if not match:
        return markdown
    level = len(match.group(1))
    rest = markdown[match.end():]
    following = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return markdown[:match.start()].rstrip() + ("\n\n" + rest[following.start():] if following else "")


def _replace_outside_code(markdown: str, cite) -> str:
    """ Replace each run of markers with cite(ids), skipping code; an empty result drops the run and its leading space """
    def replace(match):
        text = cite(list(dict.fromkeys(_marker_ids(match.group(2)))))
        return match.group(1) + text if text else ""
    parts = re.split(r"(```.*?```|`[^`\n]*`)", markdown, flags=re.S)
    return "".join(p if i % 2 else MARKER_RUN.sub(replace, p) for i, p in enumerate(parts))


def apply_citations(markdown: str, sources: list[Source], style: str) -> str:
    """ Turn [n] markers into the chosen in-text style and append the reference list """
    style = style.lower()
    if style not in STYLES:
        raise ValueError(f"Unknown citation style '{style}', expected one of {STYLES}")
    markdown = strip_references_section(markdown)
    by_id = {s.id: s for s in sources}
    if not by_id:
        return _replace_outside_code(markdown, lambda ids: "")

    cited: list[int] = []
    def collect(ids):
        cited.extend(i for i in ids if i in by_id and i not in cited)
        return "x"
    _replace_outside_code(markdown, collect)
    listed = [by_id[i] for i in cited] or sources

    if style == "ieee":
        numbers = {s.id: n for n, s in enumerate(listed, start=1)}
        def to_ieee(ids):
            return ", ".join(f"[{n}]" for n in sorted(numbers[i] for i in ids if i in numbers))
        body = _replace_outside_code(markdown, to_ieee)
        entries = [ieee_entry(s, numbers[s.id]) for s in listed]
    else:
        years = _apa_years(listed)
        def to_apa(ids):
            parts = sorted((f"{apa_label(by_id[i])}, {years[i]}" for i in ids if i in years), key=lambda p: p.lstrip("*").lower())
            return "(" + "; ".join(parts) + ")" if parts else ""
        body = _replace_outside_code(markdown, to_apa)
        entries = [_apa_suffix(apa_entry(s), s, years) for s in sorted(listed, key=_apa_sort_key)]

    return body.rstrip() + "\n\n## References\n\n" + "\n\n".join(entries) + "\n"


def _apa_suffix(entry: str, source: Source, years: dict[int, str]) -> str:
    """ Same author and year twice: the a/b suffix goes on the date in the list too """
    year = years[source.id]
    if year in (_year(source), "n.d."):
        return entry
    date = _apa_date(source)
    suffix = year[len(_year(source)):]
    new = date.replace(_year(source), _year(source) + suffix, 1) if date != "n.d." else f"n.d.{suffix}"
    return entry.replace(f"({date})", f"({new})", 1)
