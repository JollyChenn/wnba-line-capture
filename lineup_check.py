# lineup_check.py — resolve "questionable" pick players at LINEUP time. ESPN's confirmed
# actives (boxscore.players) populate ~30 min pre-tip; once up, a questionable player
# resolves to PLAYING or SCRATCHED. Before that, hold. Run near tip (or it says so).
import urllib.request, json, re, csv

H = {"User-Agent": "Mozilla/5.0"}
SUM = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"


def key_of(n):
    p = re.sub(r"[^a-z .'-]", "", n.lower()).replace(".", " ").split()
    return (p[0][0] + " " + p[-1]) if len(p) >= 2 else n.lower()


def getj(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20))


# ESPN injury status
inj = {}
try:
    for tm in getj(INJ).get("injuries", []):
        for it in tm.get("injuries", []):
            a = (it.get("athlete") or {}).get("displayName")
            if a:
                inj[key_of(a)] = (it.get("status") or "").lower()
except Exception:
    pass


def status(k):
    s = inj.get(k, "")
    if "out" in s or "doubtful" in s:
        return "OUT"
    if any(w in s for w in ["quest", "day-to-day", "day to day", "game-time", "game time", "probable", "coach"]):
        return "QUEST"
    return "OK"


# our pick players + their game ids (latest slate)
rows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8")))
latest = max(r["pick_date"] for r in rows)
players = {}
for r in rows:
    if r["pick_date"] == latest:
        players.setdefault(key_of(r["player"]), (r["player"], r["game_id"]))

# confirmed actives per game (cached)
lineup = {}


def actives(gid):
    if gid in lineup:
        return lineup[gid]
    acts = set()
    try:
        for tm in getj(SUM + str(gid)).get("boxscore", {}).get("players", []):
            for st in tm.get("statistics", []):
                for a in st.get("athletes", []):
                    nm = (a.get("athlete") or {}).get("displayName")
                    if nm:
                        acts.add(key_of(nm))
    except Exception:
        pass
    lineup[gid] = (acts, len(acts) > 0)
    return lineup[gid]


print(f"resolving questionable pick players at lineup time (slate {latest})\n")
quest = [(k, v) for k, v in players.items() if status(k) == "QUEST"]
if not quest:
    print("  no questionable pick players right now.")
for k, (name, gid) in quest:
    acts, posted = actives(gid)
    if not posted:
        verdict = "lineup NOT up yet -> hold; re-run ~30 min pre-tip"
    elif k in acts:
        verdict = "CONFIRMED PLAYING -> bet OK"
    else:
        verdict = "SCRATCHED (not in actives) -> DROP"
    print(f"  {name:20} game {gid}  {verdict}")
outs = [v[0] for k, v in players.items() if status(k) == "OUT"]
if outs:
    print("\n  already OUT (dropped):", ", ".join(outs))
