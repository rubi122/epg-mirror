#!/usr/bin/env python3
"""Merge ilextra (yes i24/kalkala/channel16 + HOT CMS channels) into corrected.xml.
Strips stale tvteam blocks for those ids and appends the fresh Mac-built feed."""
import re
import sys

REPLACE_IDS = {
    "ch2824", "ch3134", "channel16", "ch1171",
    # HOT CMS
    "ch1147", "ch1163", "ch1173", "ch1139", "ch1174",
    "ch1161", "ch1172", "ch1140", "ch1192", "ch1133",
    "ch1153", "ch1144", "ch1142", "ch1178", "ch1182",
    "ch1175", "ch2630",
    # Cellcom (live-block fallback when tvteam has no forward data)
    "ch2499", "ch2639", "ch2495", "ch2494", "ch2640",
}


def strip_ids(xml, ids):
    for cid in ids:
        xml = re.sub(r'<channel id="%s">.*?</channel>\s*' % re.escape(cid), "", xml, flags=re.S)
        xml = re.sub(r'<programme[^>]*channel="%s".*?</programme>\s*' % re.escape(cid), "", xml, flags=re.S)
    return xml


def main():
    base, extra, out = sys.argv[1], sys.argv[2], sys.argv[3]
    b = open(base, encoding="utf-8", errors="replace").read()
    e = open(extra, encoding="utf-8", errors="replace").read()
    b = strip_ids(b, REPLACE_IDS)
    m = re.search(r"<tv[^>]*>(.*)</tv>", e, re.S)
    frag = m.group(1) if m else ""
    idx = b.rfind("</tv>")
    if idx == -1:
        open(out, "w", encoding="utf-8").write(b); return
    open(out, "w", encoding="utf-8").write(b[:idx] + frag + b[idx:])


if __name__ == "__main__":
    main()
