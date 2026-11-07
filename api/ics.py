#!/usr/bin/env python3
"""build a subscribable ics of turkish women's volleyball matches from the tvf fixture site"""
import hashlib
import html
import re
import sys
import time
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timedelta, timezone

BASE = "https://fikstur.tvf.org.tr"
# league code (base64 in tvf links) -> name; the season part of the link changes every year
LEAGUES = {"U1VMVEFOTEFS": "Sultanlar Ligi", "QVNLVks%3d": "Kupa Voley"}
FIELDS = ["gtarih", "gsaat", "gtvkanali", "gevsahibi", "gmisafir"]
TR = timezone(timedelta(hours=3))  # turkey has no dst


def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse(page):
    cells = {}
    for field, row, val in re.findall(r'<span id="\w+?gvmusabakaliste_(\w+?)_(\d+)"[^>]*>(.*?)</span>', page, re.S):
        cells.setdefault(int(row), {})[field] = clean(val)
    for row in sorted(cells):
        c = cells[row]
        if not re.fullmatch(r"\d\d\.\d\d\.\d{4}", c.get("gtarih", "")):
            continue  # week header rows
        hhmm = c.get("gsaat", "")
        if hhmm and not re.fullmatch(r"\d\d:\d\d", hhmm):
            continue  # "Tehir" = postponed, tvf adds the new date later
        start = datetime.strptime(f"{c['gtarih']} {hhmm or '00:00'}", "%d.%m.%Y %H:%M").replace(tzinfo=TR)
        yield {f: c.get(f, "") for f in FIELDS} | {"start": start, "allday": not hhmm}


def channels(m):
    # tvf joins simulcasts: "TVF Voleybol TV-Tabii Spor"
    return {c.strip() for c in m["gtvkanali"].split("-") if c.strip()}


def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def keeper(query):
    q = parse_qs(query, keep_blank_values=True)
    if not {"lig", "kanal", "takim"} & q.keys():
        # shortcut: bare link stays trt-only so existing subscribers keep their calendar, drop once they migrate
        return lambda league, m: m["gtvkanali"].startswith("TRT")
    want = {k: {v for v in q.get(k, []) if v} for k in ("lig", "kanal", "takim")}  # empty group = no filter
    return lambda league, m: ((not want["lig"] or league in want["lig"])
                              and (not want["kanal"] or bool(channels(m) & want["kanal"]))
                              and (not want["takim"] or bool({m["gevsahibi"], m["gmisafir"]} & want["takim"])))


def ics(matches, keep):
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//voleybol-takvim//TR",
           "X-WR-CALNAME:Kadın Voleybol", "X-WR-TIMEZONE:Europe/Istanbul",
           "REFRESH-INTERVAL;VALUE=DURATION:PT6H"]
    seen = {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for league, m in matches:
        key = f"{league}|{m['gevsahibi']}|{m['gmisafir']}"
        seen[key] = seen.get(key, 0) + 1  # same pairing can repeat in playoffs
        uid = hashlib.sha1(f"{key}|{seen[key]}".encode()).hexdigest()
        if not keep(league, m):
            continue  # after the uid counter so filtering never shifts uids
        channel = m["gtvkanali"] or "belli değil"
        title = f"{m['gevsahibi']} - {m['gmisafir']}"
        if m["allday"]:
            when = [f"DTSTART;VALUE=DATE:{m['start']:%Y%m%d}"]
        else:
            start = m["start"].astimezone(timezone.utc)
            when = [f"DTSTART:{start:%Y%m%dT%H%M%SZ}",
                    f"DTEND:{start + timedelta(hours=2):%Y%m%dT%H%M%SZ}"]
        out += ["BEGIN:VEVENT", f"UID:{uid}@voleybol-takvim", f"DTSTAMP:{stamp}", *when,
                f"SUMMARY:{esc(title)}",
                f"DESCRIPTION:{esc(f'{league}\nKanal: {channel}')}",
                "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "voleybol-takvim"})
    return urllib.request.urlopen(req, timeout=60).read().decode("cp1254")


def current_matches():
    home = fetch("/Fikst%C3%BCr")
    links = {link.split("/")[3]: link for link in re.findall(r'FSW/[^"\']+', home)}
    assert LEAGUES.keys() <= links.keys(), "tvf fixture links not found"
    matches = [(name, m) for code, name in LEAGUES.items() for m in parse(fetch("/" + links[code]))]
    # guard: a broken parse must not serve an empty calendar that wipes the subscriber's events
    assert len(matches) > 50, f"only {len(matches)} matches parsed"
    return matches


_cache = (0.0, [])


def build(query=""):
    # every filter combo is its own cdn cache key, so share one tvf download per warm instance per hour
    global _cache
    if time.time() - _cache[0] > 3600:
        _cache = (time.time(), current_matches())
    return ics(_cache[1], keeper(query))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            body, status, ctype = build(urlparse(self.path).query).encode(), 200, "text/calendar; charset=utf-8"
        except Exception as e:
            # 5xx makes google keep the last good copy
            body, status, ctype = f"tvf fetch failed: {e}".encode(), 502, "text/plain"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        # vercel edge cache: hit tvf at most hourly
        self.send_header("Cache-Control", "public, s-maxage=3600, stale-while-revalidate=86400")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    sys.stdout.write(build(sys.argv[1] if len(sys.argv) > 1 else ""))
