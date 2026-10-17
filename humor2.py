#!/usr/bin/env python3
"""
Build an XMLTV feed for "ערוץ ההומור 2" (yes channel CN63) from the official
yes broadcast-schedule JSON API, so iSTB can show its correct guide.

Output channel id: humor2il  (assign the iSTB channel to this id)
Usage: humor2.py output.xml [days]
"""
import sys
import json
import datetime
import urllib.request

CHANNEL_ID = "humor2il"
YES_SITE_ID = "CN63"
DISPLAY_NAMES = ["ערוץ ההומור 2", " ערוץ ההומור 2", "Humor Channel 2", "IL: CELLCOM HUMOR 2"]
UA = ("Mozilla/5.0 (Linux; Linux x86_64) AppleWebKit/600.3 "
      "(KHTML, like Gecko) Chrome/48.0.2544.291 Safari/600")


def fetch_day(date_str):
    url = ("https://svc.yes.co.il/api/content/broadcast-schedule/channels/"
           f"{YES_SITE_ID}?date={date_str}&ignorePastItems=false")
    req = urllib.request.Request(url, headers={
        "user-agent": UA,
        "accept-language": "he-IL",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data.get("items", []) or []


def to_xmltv_time(iso):
    # "2026-08-29T14:09:00Z" -> "20260829140900 +0000"
    dt = datetime.datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%Y%m%d%H%M%S") + " +0000"


def xml_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def main():
    out = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    today = datetime.date.today()
    seen = set()
    programmes = []
    for i in range(days):
        d = today + datetime.timedelta(days=i)
        ds = f"{d.year}-{d.month}-{d.day}"
        try:
            items = fetch_day(ds)
        except Exception as e:
            sys.stderr.write(f"warn: day {ds} failed: {e}\n")
            continue
        for it in items:
            start = it.get("starts")
            stop = it.get("ends")
            if not start or not stop:
                continue
            key = (start, stop, it.get("title"))
            if key in seen:
                continue
            seen.add(key)
            programmes.append(it)

    programmes.sort(key=lambda x: x.get("starts") or "")

    with open(out, "w", encoding="utf-8") as o:
        o.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        o.write('<tv generator-info-name="humor2-yes">\n')
        o.write(f'  <channel id="{CHANNEL_ID}">\n')
        for nm in DISPLAY_NAMES:
            o.write(f'    <display-name>{xml_escape(nm)}</display-name>\n')
        o.write('  </channel>\n')
        for it in programmes:
            start = to_xmltv_time(it["starts"])
            stop = to_xmltv_time(it["ends"])
            title = xml_escape(it.get("title"))
            desc = xml_escape(it.get("description"))
            o.write(f'  <programme start="{start}" stop="{stop}" channel="{CHANNEL_ID}">\n')
            o.write(f'    <title lang="he">{title}</title>\n')
            if desc:
                o.write(f'    <desc lang="he">{desc}</desc>\n')
            o.write('  </programme>\n')
        o.write('</tv>\n')

    sys.stderr.write(f"wrote {len(programmes)} programmes to {out}\n")


if __name__ == "__main__":
    main()
