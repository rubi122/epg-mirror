#!/usr/bin/env python3
"""
Pull forward EPG for HOT Israeli channels from hot.net.il CMS API
(ProgramsSchedual) and emit XMLTV using the same channel ids iSTB already
assigns (ch1147 HOT3, ch1163 Bidur, etc.).

tvteam/il.xml often runs out of forward data for these; HOT's own API stays fresh.

Usage: hotextra.py output.xml [days]
"""
import sys
import json
import datetime
import urllib.request
from zoneinfo import ZoneInfo
from collections import defaultdict

IL = ZoneInfo("Asia/Jerusalem")
UA = "Mozilla/5.0"

# HOT CMS channelID -> iSTB / il.xml.gz EPG id
HOT_MAP = {
    "160": "ch1147",  # HOT3
    "550": "ch1163",  # HOT Bidur
    "555": "ch1173",  # HOT Real
    "127": "ch1139",  # HOT Zone
    "243": "ch1174",  # HOT Comedy Central
    "129": "ch1161",  # HOT Cinema 1
    "130": "ch1172",  # HOT Cinema 2
    "131": "ch1140",  # HOT Cinema 3
    "228": "ch1192",  # HOT Cinema 4
    "666": "ch1133",  # HOT Cinema Israeli
    "606": "ch1153",  # HOT Family / Cinema Family
    "286": "ch1144",  # HOT 8
    "597": "ch1142",  # Channel 24
    "543": "ch1178",  # Humor Channel
    "441": "ch1182",  # Reality
    "567": "ch2630",  # Foody
    "500": "ch1134",  # Sport 5 Plus / 5PLUS
}

NAMES = {
    "ch1147": ["IL: HOT 3 HD", " HOT 3 HD", "HOT 3"],
    "ch1163": ["IL: HOT Bidur HD", " HOT Bidur HD", "HOT Bidur"],
    "ch1173": ["IL: HOT Real HD", " HOT Real HD"],
    "ch1139": ["IL: HOT Zone HD", " HOT Zone HD"],
    "ch1174": ["IL: HOT Comedy Central HD", " HOT Comedy Central HD"],
    "ch1161": ["IL: HOT Cinema 1 HD", " HOT Cinema 1 HD"],
    "ch1172": ["IL: HOT Cinema 2 HD", " HOT Cinema 2 HD"],
    "ch1140": ["IL: HOT Cinema 3 HD", " HOT Cinema 3 HD"],
    "ch1192": ["IL: HOT Cinema 4 HD", " HOT Cinema 4 HD"],
    "ch1133": ["IL: HOT Cinema Israeli HD", " HOT Cinema Israeli HD"],
    "ch1153": ["IL: HOT Cinema Family HD", " HOT Cinema Family HD", "HOT Family"],
    "ch1144": ["IL: HOT 8 HD", " HOT 8 HD"],
    "ch1142": ["IL: Channel 24", " Channel 24", "Channel 24"],
    "ch1178": ["IL: Humor Channel", " Humor Channel"],
    "ch1182": ["IL: Reality HD", " Reality HD"],
    "ch2630": ["IL: Foody HD", " Foody HD", "Foody"],
    "ch1134": ["IL: Sport 5 Plus", " Sport 5 Plus", "Sport 5 Plus"],
}


def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        obj = json.loads(r.read().decode())
    if isinstance(obj, str):
        obj = json.loads(obj)
    return obj


def parse_hot_dt(s):
    return datetime.datetime.strptime(s, "%Y/%m/%d %H:%M:%S").replace(tzinfo=IL)


def to_xmltv(dt_local):
    utc = dt_local.astimezone(datetime.timezone.utc)
    return utc.strftime("%Y%m%d%H%M%S") + " +0000"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def collect(days):
    today = datetime.datetime.now(IL).date()
    start = f"{today.year}/{today.month:02d}/{today.day:02d} 00:00:00"
    end_d = today + datetime.timedelta(days=max(1, days) - 1)
    end = f"{end_d.year}/{end_d.month:02d}/{end_d.day:02d} 23:59:59"
    pr = post(
        "https://www.hot.net.il/HotCmsApiFront/api/ProgramsSchedual/GetProgramsSchedual",
        {"ProgramsStartDateTime": start, "ProgramsEndDateTime": end},
    )
    pdata = pr.get("data")
    if isinstance(pdata, str):
        pdata = json.loads(pdata)
    arr = pdata.get("programsDetails") or []
    by = defaultdict(list)
    seen = set()
    for p in arr:
        istb = HOT_MAP.get(str(p.get("channelID") or ""))
        if not istb:
            continue
        try:
            st = parse_hot_dt(p["programStartTime"])
            en = parse_hot_dt(p["programEndTime"])
        except Exception:
            continue
        key = (istb, st.isoformat(), en.isoformat(), p.get("programTitle"))
        if key in seen:
            continue
        seen.add(key)
        by[istb].append((st, en, p.get("programTitle") or "", p.get("synopsis") or ""))
    for v in by.values():
        v.sort(key=lambda x: x[0])
    return by


def main():
    outp = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    by = collect(days)
    total = 0
    with open(outp, "w", encoding="utf-8") as o:
        o.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        o.write('<tv generator-info-name="hotextra">\n')
        for cid in sorted(set(HOT_MAP.values())):
            o.write(f'  <channel id="{cid}">\n')
            for nm in NAMES.get(cid, [cid]):
                o.write(f'    <display-name>{esc(nm)}</display-name>\n')
            o.write("  </channel>\n")
        for cid, items in by.items():
            sys.stderr.write(f"{cid}: {len(items)} programmes\n")
            for st, en, title, desc in items:
                total += 1
                o.write(
                    f'  <programme start="{to_xmltv(st)}" stop="{to_xmltv(en)}" '
                    f'channel="{cid}">\n'
                )
                o.write(f'    <title lang="he">{esc(title)}</title>\n')
                if desc:
                    o.write(f'    <desc lang="he">{esc(desc)}</desc>\n')
                o.write("  </programme>\n")
        o.write("</tv>\n")
    sys.stderr.write(f"wrote {total} programmes to {outp}\n")
    return 0 if total >= 50 else 2


if __name__ == "__main__":
    sys.exit(main())
