# cbs_check.py — second-source the player stats. Pull per-player MPG/PPG/GP from
# CBS Sports and cross-check against OUR box_2026 (ESPN-derived). Confirms the
# minutes (the shrink signal!) + scoring the model relies on. Flags divergence.
#   python cbs_check.py [cbs_team_stats_url]   (default = Toronto Tempo)
import csv, re, html, sys
from collections import defaultdict
from curl_cffi import requests as creq

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.cbssports.com/wnba/teams/TOR/toronto-tempo/stats/"


def key_of(name):
    parts = re.sub(r"[^a-z .]", "", name.lower()).replace(".", " ").split()
    return (parts[0][0] + " " + parts[-1]) if len(parts) >= 2 else name.lower()


# 1) CBS (independent source)
t = creq.get(URL, impersonate="chrome", timeout=25).text
i = t.find("TableBase-table")
rows = re.findall(r"<tr[^>]*>(.*?)</tr>", t[i:i + 40000], re.S)
cbs = {}
for row in rows[1:]:
    cs = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
    if len(cs) < 5:
        continue
    try:
        gp, mpg, ppg = int(cs[1]), float(cs[3]), float(cs[4])
    except ValueError:
        continue
    nm = re.search(r"([A-Z][a-z]+)\s+([A-Z][a-zA-Z'.-]+)", cs[0])   # CBS packs "B. Sykes / G / Brittney Sykes" in one cell -> take the full name
    name = f"{nm.group(1)} {nm.group(2)}" if nm else cs[0].strip()
    cbs[key_of(name)] = {"name": name, "gp": gp, "mpg": mpg, "ppg": ppg}

# 2) OURS (box_2026 season averages, ESPN-derived)
agg = defaultdict(lambda: {"min": [], "pts": []})
names = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    try:
        mn, pt = float(r["min"]), float(r["pts"])
    except (ValueError, KeyError):
        continue
    k = key_of(r["player"])
    agg[k]["min"].append(mn); agg[k]["pts"].append(pt); names[k] = r["player"]
ours = {k: {"name": names[k], "mpg": sum(d["min"]) / len(d["min"]), "ppg": sum(d["pts"]) / len(d["pts"]), "gp": len(d["min"])}
        for k, d in agg.items() if d["min"]}

# 3) cross-check
print(f"CBS players: {len(cbs)}  (source: {URL.split('/teams/')[-1].split('/stats')[0]})\n")
print(f"{'player':15}{'CBS mpg/ppg/gp':18}{'OUR mpg/ppg/gp':18}status")
print("-" * 70)
flags = 0
for k, c in sorted(cbs.items(), key=lambda x: -x[1]["mpg"]):
    o = ours.get(k)
    cbs_s = f"{c['mpg']:.1f}/{c['ppg']:.1f}/{c['gp']}"
    if not o:
        print(f"{c['name']:15}{cbs_s:18}{'-- not in ours':18}WARN missing in our data"); flags += 1; continue
    our_s = f"{o['mpg']:.1f}/{o['ppg']:.1f}/{o['gp']}"
    dm, dp = abs(c["mpg"] - o["mpg"]), abs(c["ppg"] - o["ppg"])
    st = "OK" if dm <= 3 and dp <= 4 else f"WARN dMPG {dm:.1f} dPPG {dp:.1f}"
    if st != "OK":
        flags += 1
    print(f"{c['name']:15}{cbs_s:18}{our_s:18}{st}")
print("-" * 70)
print(f"{flags} flag(s)." + ("  CBS confirms our minutes/scoring." if flags == 0 else "  Review WARNs — data gap or name mismatch."))
