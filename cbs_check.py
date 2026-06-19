# cbs_check.py — SECOND-SOURCE the player stats. Pull per-player GP/MPG/PPG from CBS Sports
# (ALL teams) and cross-check vs OUR box_2026 (ESPN-derived). Confirms the minutes (the shrink
# signal!) + scoring the model relies on; flags divergence. Informational — never blocks.
# Robust full-name key (no Chance-vs-Chelsea-Gray collision; folds accents + De/Te/A' prefixes).
#   python cbs_check.py            (all teams, default)
#   python cbs_check.py <cbs_url>  (single team)
import csv, re, html, sys, unicodedata
from collections import defaultdict
from curl_cffi import requests as creq

CBS = "https://www.cbssports.com"
POS = re.compile(r"[GFC](?:[-/][GFC])?$")             # position token marks where the abbreviated name ends


def nkey(name):                                       # robust FULL-name key: fold accents, drop punctuation, collapse spaces
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()


def cbs_name(cell):                                   # CBS packs "B. Sykes  G  Brittney Sykes" -> take the FULL name after the position
    parts = cell.split()
    last_pos = max((i for i, w in enumerate(parts) if POS.match(w)), default=-1)
    after = [w for w in parts[last_pos + 1:] if w[:1].isupper()]
    if len(after) >= 2:
        return " ".join(after)
    cap = [w for w in parts if len(w) >= 2 and w[:1].isupper()]   # fallback: last two long capitalized tokens
    return " ".join(cap[-2:]) if len(cap) >= 2 else cell.strip()


def fetch(u):
    return creq.get(u, impersonate="chrome", timeout=25).text


def team_urls():
    if len(sys.argv) > 1:
        return [sys.argv[1].replace(CBS, "")]
    idx = fetch(CBS + "/wnba/teams/")
    return sorted(set(re.findall(r"/wnba/teams/[A-Za-z]{2,4}/[a-z0-9-]+/", idx)))


# OURS: box_2026 season averages, robust full-name key
agg = defaultdict(lambda: {"min": [], "pts": []}); names = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    try:
        mn, pt = float(r["min"]), float(r["pts"])
    except (ValueError, KeyError):
        continue
    k = nkey(r["player"]); agg[k]["min"].append(mn); agg[k]["pts"].append(pt); names[k] = r["player"]
ours = {k: {"mpg": sum(d["min"]) / len(d["min"]), "ppg": sum(d["pts"]) / len(d["pts"]), "gp": len(d["min"])}
        for k, d in agg.items() if d["min"]}

try:
    urls = team_urls()
except Exception as e:
    print("cbs_check: CBS unreachable:", str(e)[:60]); sys.exit(0)

tot = match = div = miss = 0; warns = []
for u in urls:
    try:
        t = fetch(u if u.startswith("http") else CBS + u + ("stats/" if not u.endswith("stats/") else ""))
    except Exception:
        continue
    i = t.find("TableBase-table")
    if i < 0:
        continue
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", t[i:i + 40000], re.S)[1:]:
        cs = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cs) < 5:
            continue
        try:
            gp, mpg, ppg = int(cs[1]), float(cs[3]), float(cs[4])
        except ValueError:
            continue
        name = cbs_name(cs[0]); k = nkey(name); o = ours.get(k); tot += 1
        if not o:
            miss += 1; warns.append(f"  MISSING in ours: {name} (CBS {mpg:.0f}/{ppg:.0f}/{gp}gp)"); continue
        dm, dp = abs(mpg - o["mpg"]), abs(ppg - o["ppg"])
        if dm > 3 or dp > 4:
            div += 1; warns.append(f"  DIVERGE {name}: CBS {mpg:.1f}/{ppg:.1f} vs OURS {o['mpg']:.1f}/{o['ppg']:.1f} (gp {gp}/{o['gp']})")
        else:
            match += 1

print(f"cbs_check (2nd source): {tot} CBS players / {len(urls)} team(s) -> ✅{match} match · ⚠️{div} diverge · ❓{miss} missing")
for w in warns[:25]:
    print(w)
print("CBS confirms our minutes/scoring." if div == 0 else f"{div} real divergence(s) — review (minutes feed the shrink signal).")
sys.exit(0)                                           # informational; never block the workflow
