from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import asyncio
import html
import httpx
import json
import os
import re
import time

load_dotenv(override=True)

# Gemini daily quotas reset at midnight Pacific time
PACIFIC = ZoneInfo("America/Los_Angeles")
USAGE_FILE = Path(__file__).with_name(".usage.json")
RECENT_RUNS = 5


def _limit(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    return int(value) if value.isdigit() and int(value) > 0 else None


RPM = _limit("GEMINI_RPM")
RPD = _limit("GEMINI_RPD")
SEARCH_LIMIT = _limit("GEMINI_SEARCH_LIMIT")
SEARCH_PERIOD = os.getenv("GEMINI_SEARCH_PERIOD", "month").strip().lower()
if SEARCH_PERIOD not in ("day", "month"):
    raise ValueError(f"GEMINI_SEARCH_PERIOD must be 'day' or 'month', got '{SEARCH_PERIOD}'")
HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 5))
# A run without web search: planner + writer
MEMORY_RUN_CALLS = 2


class QuotaError(Exception):
    """ A run can't start or continue because the Gemini quota is used up; memory_ok: a run without web search still fits """

    def __init__(self, notice: str, memory_ok: bool = False):
        super().__init__(notice)
        self.memory_ok = memory_ok


def _duration(delta: timedelta) -> str:
    minutes = max(int(delta.total_seconds() // 60), 1)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


class FileStore:
    """ Usage counts in a local JSON file """

    def __init__(self, path: Path = USAGE_FILE):
        self.path = path

    def load(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def save(self, state: dict) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2))
            tmp.replace(self.path)
        except OSError:
            pass


class UpstashStore:
    """
    Usage counts in Upstash Redis (REST API), for hosts whose disk is wiped on restart (like Render's free plan).
    Writes go out in order on a background thread so Gemini calls aren't held up. If the first read fails,
    nothing is written, so a network error can't overwrite the saved counts with an empty state.
    """
    KEY = "deep-research:usage"

    def __init__(self, url: str, token: str, client: httpx.Client | None = None):
        self.url = url
        self.client = client or httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=10)
        self._writer = ThreadPoolExecutor(max_workers=1)
        self.available = True

    def _command(self, *args: str):
        response = self.client.post(self.url, json=list(args))
        response.raise_for_status()
        body = response.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body.get("result")

    def load(self) -> dict:
        try:
            value = self._command("GET", self.KEY)
            return json.loads(value) if value else {}
        except (httpx.HTTPError, RuntimeError, ValueError) as e:
            self.available = False
            print(f"Usage meter: couldn't read the counts from Upstash ({e}). This session's counts won't be saved.")
            return {}

    def save(self, state: dict) -> None:
        if self.available:
            self._writer.submit(self._set, json.dumps(state))

    def _set(self, data: str) -> None:
        try:
            self._command("SET", self.KEY, data)
        except (httpx.HTTPError, RuntimeError, ValueError) as e:
            print(f"Usage meter: couldn't save the counts to Upstash ({e})")


def default_store() -> FileStore | UpstashStore:
    """ Upstash when UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are set, otherwise .usage.json """
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    return UpstashStore(url, token) if url and token else FileStore()


class UsageMeter:
    """
    Counts this app's Gemini calls and Google Search grounding calls, spaces calls out to stay under the
    per-minute limit, and estimates what's left. Google doesn't report remaining quota, so these are local
    counts against the limits set in .env; calls made elsewhere on the same project aren't seen.
    """

    def __init__(self, store: FileStore | UpstashStore | None = None):
        self.enabled = False
        self.store = store or default_store()
        self._state: dict | None = None
        self._recent: deque[float] = deque()
        self._retry_at = 0.0
        self._locks: dict[int, asyncio.Lock] = {}

    @property
    def state(self) -> dict:
        """ The saved counts, read on first use (so the OpenAI provider never touches the store) """
        if self._state is None:
            self._state = self.store.load()
        return self._state

    @state.setter
    def state(self, value: dict) -> None:
        self._state = value

    # === Counting ===

    def _now(self) -> datetime:
        return datetime.now(PACIFIC)

    def _roll(self) -> dict:
        """ Start fresh counts when the day (or the search period) has changed """
        day = self._now().date().isoformat()
        period = day if SEARCH_PERIOD == "day" else day[:7]
        s = self.state
        if s.get("day") != day:
            # A search quota error is retried the next day too, in case billing was turned on
            s.update(day=day, calls=0, calls_exhausted=False, searches_exhausted=False)
        if s.get("search_period") != period:
            s.update(search_period=period, searches=0, searches_exhausted=False)
        s.setdefault("run_costs", [])
        return s

    def _save(self) -> None:
        self.store.save(self.state)

    def _lock(self) -> asyncio.Lock:
        loop = id(asyncio.get_running_loop())
        return self._locks.setdefault(loop, asyncio.Lock())

    async def acquire(self, kind: str = "call") -> None:
        """ Wait until a call fits under the per-minute limit, then count it ("search" counts as both) """
        if not self.enabled:
            return
        async with self._lock():
            while True:
                now = time.monotonic()
                while self._recent and now - self._recent[0] >= 60:
                    self._recent.popleft()
                wait = self._retry_at - now
                if RPM and len(self._recent) >= RPM:
                    wait = max(wait, 60 - (now - self._recent[0]))
                if wait <= 0:
                    break
                await asyncio.sleep(wait)
            self._recent.append(time.monotonic())
            s = self._roll()
            s["calls"] += 1
            if kind == "search":
                s["searches"] += 1
            self._save()

    async def on_request(self, request) -> None:
        """ httpx request hook for the Gemini client: every HTTP request is one call """
        await self.acquire()

    async def on_response(self, response) -> None:
        """ httpx response hook: learn from 429 responses """
        if response.status_code == 429:
            await response.aread()
            self.note_quota_error(f"429 RESOURCE_EXHAUSTED {response.text}")

    def note_quota_error(self, error, kind: str = "call") -> bool:
        """
        Record a 429: a per-minute limit pauses calls for the server's retry delay; a daily or monthly
        quota marks that quota as used up. Returns whether the error was a quota error.
        """
        text = error if isinstance(error, str) else f"{error} {getattr(error, 'body', '') or ''}"
        code = None if isinstance(error, str) else (getattr(error, "code", None) or getattr(error, "status_code", None))
        if code != 429 and "RESOURCE_EXHAUSTED" not in text:
            return False
        delay = re.search(r"retryDelay\W+(\d+(?:\.\d+)?)s", text) or re.search(r"retry in (\d+(?:\.\d+)?)s", text, re.I)
        long_quota = re.search(r"Per(?:Day|Month)", text)
        if "PerMinute" in text or (delay and not long_quota):
            self._retry_at = time.monotonic() + (float(delay.group(1)) if delay else 60)
            self.state["last_error"] = "per-minute rate limit"
        else:
            s = self._roll()
            s["searches_exhausted" if kind == "search" else "calls_exhausted"] = True
            s["last_error"] = "search quota used up" if kind == "search" else "daily call quota used up"
        self._save()
        return True

    # === Runs ===

    def snapshot(self) -> tuple[int, int]:
        s = self._roll()
        return s["calls"], s["searches"]

    def record_run(self, start: tuple[int, int]) -> None:
        """ Remember what a finished run cost, to estimate the next ones """
        if not self.enabled:
            return
        calls, searches = self.snapshot()
        cost = [calls - start[0], searches - start[1]]
        if cost[0] > 0 and cost[1] >= 0:
            self.state["run_costs"] = (self.state["run_costs"] + [cost])[-RECENT_RUNS:]
            self._save()

    def estimate_run_cost(self, web_search: bool = True) -> tuple[int, int]:
        """ (calls, searches) for one run, clarifying questions included """
        costs = self._roll()["run_costs"]
        if not web_search:
            calls, searches = MEMORY_RUN_CALLS, 0
        elif costs:
            calls = round(sum(c for c, _ in costs) / len(costs))
            searches = round(sum(s for _, s in costs) / len(costs))
        else:
            # planner + writer, and per search: tool call, grounding call, summary
            calls, searches = 2 + 3 * HOW_MANY_SEARCHES, HOW_MANY_SEARCHES
        return calls + 1, searches

    # === What's left ===

    def calls_left(self) -> int | None:
        s = self._roll()
        if s["calls_exhausted"]:
            return 0
        return max(RPD - s["calls"], 0) if RPD else None

    def searches_left(self) -> int | None:
        s = self._roll()
        if s["searches_exhausted"]:
            return 0
        return max(SEARCH_LIMIT - s["searches"], 0) if SEARCH_LIMIT else None

    def runs_left(self) -> int | None:
        calls, searches = self.estimate_run_cost()
        fits = [left // need for left, need in ((self.calls_left(), calls), (self.searches_left(), searches)) if left is not None and need]
        return min(fits) if fits else None

    def _daily_reset(self) -> str:
        now = self._now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return _duration(midnight - now)

    def _search_reset(self) -> str:
        if SEARCH_PERIOD == "day":
            return f"in {self._daily_reset()}"
        now = self._now()
        first = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        return f"on {first:%b} 1"

    def check_can_run(self, clarify: bool = True, web_search: bool = True) -> str | None:
        """ Why a run can't start (not enough calls or searches left), or None when it can """
        if not self.enabled:
            return None
        calls, searches = self.estimate_run_cost(web_search)
        if not clarify:
            calls -= 1
        calls_left, searches_left = self.calls_left(), self.searches_left()
        if calls_left is not None and calls_left < calls:
            return (f"A research run needs about {calls} Gemini calls, but only {calls_left} are left today. "
                    f"The daily quota resets at midnight Pacific time, in {self._daily_reset()}.")
        if searches_left is not None and searches_left < searches:
            return (f"A research run needs about {searches} Google searches, but only {searches_left} are left. "
                    f"The search quota resets {self._search_reset()}. "
                    "Without searches the report would have no web sources or references.")
        return None

    def quota_notice(self, reason: str | None = None) -> str:
        """ Markdown shown in place of a report when the quota stops a run """
        if reason is None:
            last = self.state.get("last_error", "")
            if last == "per-minute rate limit":
                reason = "Gemini's per-minute rate limit was hit. Wait a minute and try again."
            elif last == "search quota used up":
                reason = f"The Google Search quota is used up. It resets {self._search_reset()}."
            else:
                reason = f"The daily Gemini quota is used up. It resets at midnight Pacific time, in {self._daily_reset()}."
        return f"**Out of Gemini quota.** {reason}"

    # === Display ===

    def _calls_text(self) -> str:
        s, left = self._roll(), self.calls_left()
        used = f"{s['calls']} / {RPD}" if RPD else str(s["calls"])
        if s["calls_exhausted"]:
            return f"Calls today: {used} (used up)"
        return f"Calls today: {used} ({left} left)" if left is not None else f"Calls today: {used}"

    def _searches_text(self) -> str:
        s, left = self._roll(), self.searches_left()
        period = "today" if SEARCH_PERIOD == "day" else "this month"
        used = f"{s['searches']} / {SEARCH_LIMIT}" if SEARCH_LIMIT else str(s["searches"])
        if s["searches_exhausted"]:
            return f"Searches {period}: {used} (used up, resets {self._search_reset()})"
        return f"Searches {period}: {used} ({left} left)" if left is not None else f"Searches {period}: {used}"

    def summary_html(self, lead: str = "") -> str:
        """ The usage line under a report, after an optional first line (lead) """
        if not self.enabled:
            return f'<div class="dr-usage-line">{html.escape(lead)}</div>' if lead else ""
        parts = [self._calls_text(), self._searches_text()]
        runs = self.runs_left()
        if runs == 0:
            parts.append("not enough left for another run")
        elif runs is not None:
            parts.append(f"about {runs} more run{'' if runs == 1 else 's'}")
        parts.append(f"daily reset in {self._daily_reset()}")
        hint = "" if RPD else " Set GEMINI_RPD and GEMINI_SEARCH_LIMIT in .env to see what's left."
        note = f"Counts only this app's calls.{hint}"
        lead = f"{html.escape(lead)}<br>" if lead else ""
        return f'<div class="dr-usage-line">{lead}{html.escape(" · ".join(parts))}<br><span>{html.escape(note)}</span></div>'

    def compact_html(self) -> str:
        """ The counter in the top bar """
        if not self.enabled:
            return ""
        s, left, runs = self._roll(), self.calls_left(), self.runs_left()
        if left is not None:
            text = f"{left} calls left"
        else:
            text = f"{s['calls']} calls today"
        if runs == 0:
            text += " · no web runs left" if self.check_can_run(web_search=False) is None else " · no runs left"
        elif runs is not None:
            text += f" · ~{runs} run{'' if runs == 1 else 's'}"
        if s["searches_exhausted"] or self.searches_left() == 0:
            text += " · searches used up"
        warn = " dr-usage-warn" if runs == 0 or s["calls_exhausted"] or s["searches_exhausted"] else ""
        title = f"{self._calls_text()} · {self._searches_text()} · daily reset in {self._daily_reset()}"
        return f'<span class="dr-usage{warn}" title="{html.escape(title)}">{html.escape(text)}</span>'


meter = UsageMeter()
