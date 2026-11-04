"""Check Quarter's public services and build the status page.

Run by .github/workflows/check.yml every 10 minutes. History lives only in the
published site: each run reads the live history.json, adds one check, and
publishes again. No commits, so the repository does not grow.
"""

import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

SERVICES = [
    ("Sandbox gateway", "https://sandbox.quarterfi.com/healthz", b'"ok": true'),
    ("Rulebook feed", "https://quarterso.github.io/feed/feed.json", b'"signature"'),
    ("Website", "https://quarterfi.com/", b"Quarter"),
]
KEEP_SECONDS = 30 * 86400
DAYS = 30
SLOW_MS = 10_000


def probe(url, expect, timeout=10):
    """Milliseconds for a good answer, or None. One retry, so one dropped packet is not an outage."""
    for attempt in range(2):
        start = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"user-agent": "quarter-status"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read(5_000_000)
            if resp.status == 200 and expect in body:
                return round((time.monotonic() - start) * 1000)
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        if attempt == 0:
            time.sleep(5)
    return None


def load_history(url):
    """The published history. A missing file starts fresh; any other failure stops the run, so history is never lost."""
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"checks": []}
        raise


def add_check(history, now, results):
    checks = [c for c in history.get("checks", []) if c["t"] > now - KEEP_SECONDS]
    checks.append({"t": now, "ms": results})
    return {"checks": checks}


def daily(checks, name, now):
    """Per day, oldest first: share of good checks, or None for a day with no checks."""
    out = []
    today = now // 86400
    for day in range(today - DAYS + 1, today + 1):
        seen = [c["ms"].get(name) for c in checks if c["t"] // 86400 == day and name in c["ms"]]
        out.append(None if not seen else sum(v is not None for v in seen) / len(seen))
    return out


def uptime(checks, name):
    seen = [c["ms"][name] for c in checks if name in c["ms"]]
    return None if not seen else 100 * sum(v is not None for v in seen) / len(seen)


def render(history, now):
    checks = history["checks"]
    last = checks[-1]["ms"] if checks else {}
    down = [n for n, _, _ in SERVICES if last.get(n) is None]
    when = datetime.fromtimestamp(now, timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    rows = []
    for name, _, _ in SERVICES:
        ms = last.get(name)
        state = "Down" if ms is None else ("Slow" if ms > SLOW_MS else "Operational")
        up = uptime(checks, name)
        bars = "".join(
            f'<i class="{"n" if d is None else "u" if d == 1 else "p" if d >= 0.9 else "d"}"'
            f' title="{"no checks" if d is None else f"{d * 100:.1f}% up"}"></i>'
            for d in daily(checks, name, now)
        )
        rows.append(
            f'<section><div class="row"><h2>{html.escape(name)}</h2>'
            f'<span class="s {state.lower()}">{state}</span></div>'
            f'<div class="bars">{bars}</div>'
            f'<div class="meta"><span>30 days ago</span>'
            f'<span>{"" if up is None else f"{up:.2f}% up"}</span><span>Today</span></div></section>'
        )
    banner = (
        '<p class="banner ok">All systems operational</p>'
        if not down
        else f'<p class="banner bad">Down: {html.escape(", ".join(down))}</p>'
    )
    return PAGE.format(banner=banner, rows="\n".join(rows), when=when)


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quarter status</title>
<meta name="description" content="Live status of Quarter's public services.">
<style>
:root{{--ink:#0a1f44;--mute:#5b6b85;--line:#e3e8f0;--blue:#1d4ed8;--ok:#0f9d58;--warn:#d97706;--bad:#c62828;--none:#e3e8f0;--bg:#fff}}
@media (prefers-color-scheme:dark){{:root{{--ink:#e8eefb;--mute:#97a6c2;--line:#22304d;--none:#22304d;--bg:#0a1324}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}}
main{{max-width:760px;margin:0 auto;padding:48px 16px}}
header{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:16px}}
header a{{color:var(--ink);text-decoration:none;font-weight:600;font-size:18px}}header span{{color:var(--mute);font-size:13px}}
.banner{{margin:28px 0;padding:16px 20px;border-radius:8px;font-weight:600;color:#fff}}.ok{{background:var(--ok)}}.bad{{background:var(--bad)}}
section{{border:1px solid var(--line);border-radius:8px;padding:18px 20px;margin-bottom:12px}}
.row{{display:flex;justify-content:space-between;align-items:center}}h2{{font-size:15px;margin:0;font-weight:600}}
.s{{font-size:13px;font-weight:600}}.s.operational{{color:var(--ok)}}.s.slow{{color:var(--warn)}}.s.down{{color:var(--bad)}}
.bars{{display:flex;gap:2px;margin:14px 0 6px;height:28px}}.bars i{{flex:1;border-radius:2px}}
.u{{background:var(--ok)}}.p{{background:var(--warn)}}.d{{background:var(--bad)}}.n{{background:var(--none)}}
.meta{{display:flex;justify-content:space-between;color:var(--mute);font-size:12px}}
footer{{color:var(--mute);font-size:13px;margin-top:28px}}footer a{{color:var(--blue)}}
</style></head><body><main>
<header><a href="https://quarterfi.com/">Quarter</a><span>Updated {when}</span></header>
{banner}
{rows}
<footer>Checked every 10 minutes from outside our servers. <a href="history.json">Raw history</a>.</footer>
</main></body></html>
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "site"
    now = int(time.time())
    history = load_history(os.environ.get("STATUS_HISTORY_URL", "https://quarterso.github.io/status/history.json"))
    results = {name: probe(url, expect) for name, url, expect in SERVICES}
    history = add_check(history, now, results)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "history.json"), "w") as f:
        json.dump(history, f, separators=(",", ":"))
    with open(os.path.join(out, "index.html"), "w") as f:
        f.write(render(history, now))
    with open("down.txt", "w") as f:  # read by the workflow, not published
        f.write("\n".join(n for n, ms in results.items() if ms is None))
    for name, ms in results.items():
        print(f"{name}: {'down' if ms is None else f'{ms} ms'}")


if __name__ == "__main__":
    main()
