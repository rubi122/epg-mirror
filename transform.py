#!/usr/bin/env python3
"""
Transform a tvteam XMLTV feed so its channel display-names match how iSTB parses
the team.ga / gist playlists:
  - team.ga (IL) names are parsed WITH a leading space (", IL: X" -> " IL: X").
    So for every channel we add a leading-space variant display-name.
  - the gist (Local) names differ entirely ("Channel 14" vs "IL: Channel 14 HD"),
    so we add explicit display-name aliases for those channels.
iSTB builds channelNameToID from <display-name> elements, so adding these makes
the channels link to their guide natively on every device (no per-channel prefs).

Usage: transform.py input.xml output.xml
"""
import sys

# EPG channel id -> extra playlist display-names (Local/gist names).
LOCAL_EXTRA = {
    "ch428":  ["Channel 11"],
    "ch429":  ["Channel 12"],
    "ch430":  ["Channel 13"],
    "ch1119": ["Channel 14"],
    # i24 News (ch2824) and Kalkala 10 / Channel 10 (ch3134) are now served
    # from the fresh yes-based `ilextra` feed (ids i24news / kalkala10), merged
    # into this file by the workflow. Channel 16 is a distinct channel that is
    # NOT Kalkala 10, so it is deliberately NOT aliased to ch3134 anymore.
}


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    cur_id = None
    with open(inp, "r", encoding="utf-8", errors="replace") as f, \
         open(outp, "w", encoding="utf-8") as o:
        for line in f:
            stripped = line.strip()
            # track current channel id
            if stripped.startswith("<channel "):
                a = stripped.find('id="')
                if a != -1:
                    b = stripped.find('"', a + 4)
                    cur_id = stripped[a + 4:b]
                else:
                    cur_id = None
                o.write(line)
                continue
            # when we emit a display-name, also emit the alias variants
            if stripped.startswith("<display-name>") and stripped.endswith("</display-name>"):
                o.write(line)
                name = stripped[len("<display-name>"):-len("</display-name>")]
                # leading-space variant (matches team.ga parsed names)
                if not name.startswith(" "):
                    o.write("  <display-name> " + name + "</display-name>\n")
                # explicit Local/gist aliases for mapped channels
                if cur_id in LOCAL_EXTRA:
                    for alias in LOCAL_EXTRA[cur_id]:
                        esc = xml_escape(alias)
                        o.write("  <display-name>" + esc + "</display-name>\n")
                        o.write("  <display-name> " + esc + "</display-name>\n")
                continue
            if stripped.startswith("</channel>"):
                cur_id = None
                o.write(line)
                continue
            o.write(line)


if __name__ == "__main__":
    main()
