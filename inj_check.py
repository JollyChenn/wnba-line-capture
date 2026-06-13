# inj_check.py — cross-check injuries: ESPN vs MyGameSim. The critical catch is a
# player one source calls OUT that the other doesn't — a missed scratch = a dead bet.
import urllib.request, json, re, html
from curl_cffi import requests as creq


def key_of(name):
    parts = re.sub(r"[^a-z .'-]", "", name.lower()).replace(".", " ").split()
    return (parts[0][0] + " " + parts[-1]) if len(parts) >= 2 else name.lower()


def norm(s):
    s = (s or "").lower()
    if "out" in s or "doubtful" in s:
        return "OUT"
    if any(w in s for w in ["quest", "day-to-day", "day to day", "game-time", "game time", "probable", "coach"]):
        return "DTD"
    return "OK"


# 1) ESPN (our primary)
esp = {}
try:
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries",
        headers={"User-Agent": "Mozilla/5.0"}), timeout=20))
    for tm in d.get("injuries", []):
        for it in tm.get("injuries", []):
            a = (it.get("athlete") or {}).get("displayName")
            if a:
                esp[key_of(a)] = {"name": a, "status": norm(it.get("status"))}
except Exception as e:
    print("ESPN err:", e)

# 2) MyGameSim (independent)
mgs = {}
t = creq.get("https://www.mygamesim.com/wnba/wnba-injuries.asp", impersonate="chrome", timeout=25).text
for tbl in re.findall(r"<table.*?</table>", t, re.S):
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S):
        cs = [html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cs) < 3 or cs[0].lower() == "player":
            continue
        mgs[key_of(cs[0])] = {"name": cs[0], "status": norm(cs[2]), "raw": cs[2], "injury": cs[1]}

# our pick pool = players with recent box data; anyone else can't be bet -> status irrelevant noise
import csv
pool = set()
try:
    for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
        pool.add(key_of(r["player"]))
except Exception:
    pass

# 3) cross-check — only players in our pool matter
e_out = sum(1 for v in esp.values() if v["status"] == "OUT")
m_out = sum(1 for v in mgs.values() if v["status"] == "OUT")
print(f"ESPN: {e_out} OUT / {len(esp)} listed   |   MyGameSim: {m_out} OUT / {len(mgs)} listed")
print(f"(cross-checking only the {len(pool)} players in our pick pool — obscure/non-roster diffs ignored)\n")
print(f"{'player':22}{'ESPN':7}{'MyGameSim':11}verdict")
print("-" * 64)
warns = noise = 0
for k in sorted(set(esp) | set(mgs)):
    e = esp.get(k, {}).get("status", "—")
    m = mgs.get(k, {}).get("status", "—")
    if e in ("OK", "—") and m in ("OK", "—"):
        continue
    if k not in pool:                                   # not bettable -> ignore
        noise += 1; continue
    name = (esp.get(k) or mgs.get(k))["name"]
    if e == "OUT" and m == "OUT":
        v = "OK both OUT"
    elif e == "OUT":
        v = f"WARN ESPN OUT, MGS={m} -- verify"; warns += 1
    elif m == "OUT":
        v = f"WARN MGS OUT, ESPN={e} -- MISSED SCRATCH?"; warns += 1
    else:
        v = "both uncertain (watch lineups)"
    print(f"{name:22}{e:7}{m:11}{v}")
print("-" * 64)
print(f"{warns} disagreement(s) on pool players; {noise} non-roster diffs ignored." +
      ("  Sources agree on our players." if warns == 0 else "  Verify the WARNs before betting/fading."))
