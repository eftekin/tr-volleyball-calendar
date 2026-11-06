#!/usr/bin/env python3
"""build a subscribable ics of turkish women's volleyball matches from the tvf fixture site"""
import hashlib
import html
import re
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone

BASE = "https://fikstur.tvf.org.tr"
LEAGUES = {
    "Sultanlar Ligi": "/FSW/MjAyNi0yMDI3/Sw%3d%3d/U1VMVEFOTEFS/Vm9kYWZvbmUgU3VsdGFubGFyIExpZ2k%3d",
    "Kupa Voley": "/FSW/MjAyNi0yMDI3/Sw%3d%3d/QVNLVks%3d/QVhBIFNpZ29ydGEgS3VwYSBWb2xleSBLYWTEsW5sYXI%3d",
}
FIELDS = ["gtarih", "gsaat", "gtvkanali", "gyer", "gevsahibi", "gmisafir", "gseta", "gsetb"]
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
        time = c.get("gsaat", "")
        if time and not re.fullmatch(r"\d\d:\d\d", time):
            continue  # "Tehir" = postponed, tvf adds the new date later
        start = datetime.strptime(f"{c['gtarih']} {time or '00:00'}", "%d.%m.%Y %H:%M").replace(tzinfo=TR)
        yield {f: c.get(f, "") for f in FIELDS} | {"start": start, "allday": not time}


def esc(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics(matches):
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//voleybol-takvim//TR",
           "X-WR-CALNAME:Kadın Voleybol", "X-WR-TIMEZONE:Europe/Istanbul",
           "REFRESH-INTERVAL;VALUE=DURATION:PT6H"]
    seen = {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for league, m in matches:
        key = f"{league}|{m['gevsahibi']}|{m['gmisafir']}"
        seen[key] = seen.get(key, 0) + 1  # same pairing can repeat in playoffs
        uid = hashlib.sha1(f"{key}|{seen[key]}".encode()).hexdigest()
        title = f"🏐 {m['gevsahibi']} - {m['gmisafir']}"
        if m["gseta"]:
            title += f" ({m['gseta']}-{m['gsetb']})"
        channel = m["gtvkanali"] or "kanal belli değil"
        if m["allday"]:
            title += " · saat belli değil"
            when = [f"DTSTART;VALUE=DATE:{m['start']:%Y%m%d}"]
        else:
            start = m["start"].astimezone(timezone.utc)
            when = [f"DTSTART:{start:%Y%m%dT%H%M%SZ}",
                    f"DTEND:{start + timedelta(hours=2):%Y%m%dT%H%M%SZ}"]
        out += ["BEGIN:VEVENT", f"UID:{uid}@voleybol-takvim", f"DTSTAMP:{stamp}", *when,
                f"SUMMARY:{esc(title + ' · ' + channel)}",
                f"LOCATION:{esc(m['gyer'])}",
                f"DESCRIPTION:{esc(f'{league}\nKanal: {channel}')}",
                "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def fetch(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "voleybol-takvim"})
    return urllib.request.urlopen(req, timeout=60).read().decode("cp1254")


def build():
    matches = [(name, m) for name, path in LEAGUES.items() for m in parse(fetch(path))]
    # guard: a broken parse must not serve an empty calendar that wipes the subscriber's events
    assert len(matches) > 50, f"only {len(matches)} matches parsed"
    return ics(matches)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            body, status, ctype = build().encode(), 200, "text/calendar; charset=utf-8"
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
    sys.stdout.write(build())
