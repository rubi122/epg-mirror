#!/usr/bin/env python3
"""
Build an XMLTV feed for a few Israeli channels that the epg.team mirror
(il.xml.gz) does not carry with reliable forward data, using the official
yes broadcast-schedule JSON API (reachable only from an Israeli IP).

Channels:
  i24news   <- yes CN28  (i24 Hebrew / "IL: i24 News")
  kalkala10 <- yes CN32  (Economics 10 / "IL: Kalkala 10 HD" / "Channel 10")
  channel16 <- Univtec EPG when the channel enables it; otherwise a live-block
               guide so iSTB shows something in Favorites (Channel 16 has no
               public XMLTV yet — official CMS still has enableEpg=false).

Assign the iSTB channels to these ids via long-press -> Assign EPG.

Usage: ilextra.py output.xml [days]
"""
import sys
import json
import datetime
import urllib.request
from zoneinfo import ZoneInfo

# feed channel id -> (yes site id or None, [display-names])
# NOTE: i24 and Kalkala 10 reuse the SAME EPG ids the iSTB channels are already
# assigned to (ch2824 / ch3134). The workflow's merge step strips the stale
# tvteam ch2824/ch3134 blocks and substitutes these fresh yes-based ones, so
# "IL: i24 News" and "Channel 10" get fresh forward EPG with NO in-app change.
CHANNELS = [
    ("ch2824", "CN28", [
        "IL: i24 News", " IL: i24 News", "i24 News", " i24 News",
        "i24 Hebrew", "i24 News HD",
    ]),
    ("ch3134", "CN32", [
        "IL: Kalkala 10 HD", " IL: Kalkala 10 HD", "Channel 10", " Channel 10",
        "Kalkala 10", "Economics 10",
    ]),
    ("ch1171", "YS17", [
        "IL: Kan Chinuchit 23", " IL: Kan Chinuchit 23", "Kan Chinuchit 23",
        "Channel 23", " Channel 23", "ערוץ 23", "YES 23",
    ]),
    ("channel16", None, [
        "IL: Channel 16", " IL: Channel 16", "Channel 16", " Channel 16",
        "ערוץ 16",
    ]),
    # tvteam stopped publishing forward data for these; hourly live blocks
    # until a public Cellcom/HOT-HBO source is found.
    ("ch2499", "live", [
        "IL: Cellcom Israel", " Cellcom Israel", "Cellcom Israel",
    ]),
    ("ch2639", "live", [
        "IL: Cellcom TV Shows HD", " Cellcom TV Shows HD",
    ]),
    ("ch2495", "live", [
        "IL: Cellcom Movies Action HD", " Cellcom Movies Action HD",
    ]),
    ("ch2494", "live", [
        "IL: Cellcom Movies Drama HD", " Cellcom Movies Drama HD",
    ]),
    ("ch2640", "live", [
        "IL: Cellcom Doco HD", " Cellcom Doco HD",
    ]),
    ("ch1175", "live", [
        "IL: HOT HBO HD", " HOT HBO HD", "HOT HBO",
    ]),
]

LIVE_LABELS = {
    "ch2499": ("שידור חי · Cellcom Israel", "סלקום ישראל — לוח מפורט לא זמין כרגע ממקור ציבורי."),
    "ch2639": ("שידור חי · Cellcom TV Shows", "סלקום סדרות — לוח מפורט לא זמין כרגע."),
    "ch2495": ("שידור חי · Cellcom Movies Action", "סלקום סרטים אקשן — לוח מפורט לא זמין כרגע."),
    "ch2494": ("שידור חי · Cellcom Movies Drama", "סלקום סרטים דרמה — לוח מפורט לא זמין כרגע."),
    "ch2640": ("שידור חי · Cellcom Doco", "סלקום דוקו — לוח מפורט לא זמין כרגע."),
    "ch1175": ("שידור חי · HOT HBO", "HOT HBO — לא מופיע יותר ב-API של HOT; בלוק חי זמני."),
}

UA = ("Mozilla/5.0 (Linux; Linux x86_64) AppleWebKit/600.3 "
      "(KHTML, like Gecko) Chrome/48.0.2544.291 Safari/600")

IL = ZoneInfo("Asia/Jerusalem")
CH16_GUID = "8669cd2f-dc9b-4ce9-a086-96d0c904c6c0"
CH16_DESC = (
    "ערוץ 16 בשידור חי. לוח מפורט עדיין לא מפורסם רשמית — "
    "בין התכנים: מהדורת חדשות (יעקב אילון), רצועת בוקר, "
    "״דברו אליי״, ושידורים חוזרים."
)


def fetch_day(site_id, date_str):
    url = ("https://svc.yes.co.il/api/content/broadcast-schedule/channels/"
           f"{site_id}?date={date_str}&ignorePastItems=false")
    req = urllib.request.Request(url, headers={
        "user-agent": UA,
        "accept-language": "he-IL",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return data.get("items", []) or []


def to_xmltv_time(iso):
    dt = datetime.datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%Y%m%d%H%M%S") + " +0000"


def to_xmltv_dt(dt):
    """Aware datetime -> XMLTV start/stop in +0000."""
    utc = dt.astimezone(datetime.timezone.utc)
    return utc.strftime("%Y%m%d%H%M%S") + " +0000"


def xml_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def collect(site_id, days):
    today = datetime.date.today()
    seen = set()
    out = []
    for i in range(days):
        d = today + datetime.timedelta(days=i)
        ds = f"{d.year}-{d.month}-{d.day}"
        try:
            items = fetch_day(site_id, ds)
        except Exception as e:
            sys.stderr.write(f"warn: {site_id} day {ds} failed: {e}\n")
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
            out.append(it)
    out.sort(key=lambda x: x.get("starts") or "")
    return out


def _parse_univtec_event(ev):
    start = ev.get("start")
    end = ev.get("end")
    title = ev.get("title") or "ערוץ 16"
    if not start or not end or title == "No Display":
        return None
    desc = ev.get("description") or ""
    custom = ev.get("custom") or {}
    if isinstance(custom, dict):
        desc = custom.get("longDescription") or desc or custom.get("genre") or ""
    # Univtec times are ISO; normalize to Zulu-ish for to_xmltv_time
    def norm(s):
        s = str(s).replace("Z", "")
        if "+" in s[10:]:
            s = s.split("+")[0]
        if "." in s:
            s = s.split(".")[0]
        if "T" not in s:
            return None
        # pad seconds
        parts = s.split("T")
        if len(parts[1].split(":")) == 2:
            s = s + ":00"
        return s

    ns, ne = norm(start), norm(end)
    if not ns or not ne:
        return None
    return {
        "starts": ns if ns.endswith("Z") or True else ns,
        "ends": ne,
        "title": title,
        "description": desc,
        "_xml_start": None,  # filled below via ISO parse with tz
        "_raw_start": start,
        "_raw_end": end,
    }


def fetch_univtec_ch16():
    """Return programme dicts if Channel 16 CMS ever publishes epgObject.events."""
    url = "https://insight-api-frankly.univtec.com/interface/epg"
    req = urllib.request.Request(url, headers={
        "user-agent": UA,
        "accept": "application/json",
        "x-tenant-id": "ch16israel",
        "platform": "web",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as e:
        sys.stderr.write(f"warn: univtec epg failed: {e}\n")
        return []

    channels = data if isinstance(data, list) else []
    events = []
    for ch in channels:
        guid = str(ch.get("guid") or "")
        title = str(ch.get("title") or "")
        if guid != CH16_GUID and "16" not in title and "ערוץ 16" not in title:
            continue
        eo = ch.get("epgObject") or {}
        if isinstance(eo, str):
            try:
                eo = json.loads(eo)
            except Exception:
                eo = {}
        for ev in (eo.get("events") or []):
            parsed = _parse_univtec_event(ev)
            if not parsed:
                continue
            # Prefer raw ISO with timezone via datetime
            try:
                sdt = datetime.datetime.fromisoformat(
                    str(ev["start"]).replace("Z", "+00:00"))
                edt = datetime.datetime.fromisoformat(
                    str(ev["end"]).replace("Z", "+00:00"))
                if sdt.tzinfo is None:
                    sdt = sdt.replace(tzinfo=IL)
                if edt.tzinfo is None:
                    edt = edt.replace(tzinfo=IL)
                parsed["_xml_start"] = to_xmltv_dt(sdt)
                parsed["_xml_stop"] = to_xmltv_dt(edt)
            except Exception:
                parsed["_xml_start"] = to_xmltv_time(parsed["starts"])
                parsed["_xml_stop"] = to_xmltv_time(parsed["ends"])
            events.append(parsed)
    return events


def _is_shabbat_hour(local_dt):
    """Rough Shabbat window in Israel: Fri 19:00 .. Sat 20:00 (no broadcast)."""
    wd = local_dt.weekday()  # Mon=0 .. Sun=6
    h = local_dt.hour
    if wd == 4 and h >= 19:  # Friday evening
        return True
    if wd == 5 and h < 20:  # Saturday until ~Motzei
        return True
    return False


def generate_live_blocks(days, title, desc, shabbat=False):
    """Hourly live blocks so iSTB guide is never empty."""
    now = datetime.datetime.now(IL).replace(minute=0, second=0, microsecond=0)
    start0 = now.replace(hour=0)
    end0 = start0 + datetime.timedelta(days=days)
    out = []
    t = start0
    while t < end0:
        nxt = t + datetime.timedelta(hours=1)
        if shabbat and _is_shabbat_hour(t):
            tt, dd = "אין שידור · שבת", "הערוץ אינו משדר בשבת."
        else:
            tt, dd = title, desc
        out.append({
            "title": tt,
            "description": dd,
            "_xml_start": to_xmltv_dt(t),
            "_xml_stop": to_xmltv_dt(nxt),
        })
        t = nxt
    return out


def collect_channel16(days):
    real = fetch_univtec_ch16()
    if real:
        sys.stderr.write(f"channel16: univtec {len(real)} programmes\n")
        return real
    blocks = generate_live_blocks(days, "שידור חי · ערוץ 16", CH16_DESC, shabbat=True)
    sys.stderr.write(f"channel16: live-blocks {len(blocks)} programmes "
                     "(no public EPG source yet)\n")
    return blocks


def collect_live_fallback(cid, days):
    title, desc = LIVE_LABELS[cid]
    blocks = generate_live_blocks(days, title, desc, shabbat=False)
    sys.stderr.write(f"{cid}: live-blocks {len(blocks)} programmes "
                     "(no forward public EPG)\n")
    return blocks


def write_programme(o, cid, it):
    if it.get("_xml_start") and it.get("_xml_stop"):
        start, stop = it["_xml_start"], it["_xml_stop"]
    else:
        start = to_xmltv_time(it["starts"])
        stop = to_xmltv_time(it["ends"])
    title = xml_escape(it.get("title"))
    desc = xml_escape(it.get("description"))
    o.write(f'  <programme start="{start}" stop="{stop}" channel="{cid}">\n')
    o.write(f'    <title lang="he">{title}</title>\n')
    if desc:
        o.write(f'    <desc lang="he">{desc}</desc>\n')
    o.write('  </programme>\n')


def main():
    outp = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    total = 0
    with open(outp, "w", encoding="utf-8") as o:
        o.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        o.write('<tv generator-info-name="ilextra-yes">\n')
        for cid, site, names in CHANNELS:
            o.write(f'  <channel id="{cid}">\n')
            for nm in names:
                o.write(f'    <display-name>{xml_escape(nm)}</display-name>\n')
            o.write('  </channel>\n')
        for cid, site, names in CHANNELS:
            if cid == "channel16":
                progs = collect_channel16(days)
            elif site == "live":
                progs = collect_live_fallback(cid, days)
            elif not site:
                continue
            else:
                progs = collect(site, days)
                sys.stderr.write(f"{cid} ({site}): {len(progs)} programmes\n")
            total += len(progs)
            for it in progs:
                write_programme(o, cid, it)
        o.write('</tv>\n')

    sys.stderr.write(f"wrote {total} programmes to {outp}\n")
    # exit code signals whether we got enough real data to publish
    return 0 if total >= 20 else 2


if __name__ == "__main__":
    sys.exit(main())
