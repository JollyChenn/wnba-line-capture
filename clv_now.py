# clv_now.py — for our identified bets: pull the ESPN result (did it win?) and show
# whatever line data the cloud captured (for CLV vs the close).
import urllib.request, json, csv, os
H = {"User-Agent": "Mozilla/5.0"}


def getj(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=25))


# (player, game_id, market, side, line we'd have bet)
BETS = [("Shakira Austin", "401856990", "pts", "Under", 15.5),
        ("Angel Reese", "401856991", "pra", "Over", 29.5),
        ("Chennedy Carter", "401856987", "pts", None, None)]


def result(gid, player, mkt):
    s = getj("https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event=" + gid)
    comp = (s.get("header", {}).get("competitions") or [{}])[0]
    st = comp.get("status", {}).get("type", {})
    state, detail = st.get("state"), st.get("detail")
    if state != "post":
        return state, detail, None
    for tm in s.get("boxscore", {}).get("players", []):
        for stt in tm.get("statistics", []):
            names = stt.get("names", [])
            for a in stt.get("athletes", []):
                if player in ((a.get("athlete") or {}).get("displayName", "")):
                    d = dict(zip(names, a.get("stats", [])))
                    pts = float(d.get("PTS") or 0); reb = float(d.get("REB") or 0); ast = float(d.get("AST") or 0)
                    val = {"pts": pts, "pra": pts + reb + ast}[mkt] if mkt in ("pts", "pra") else pts
                    return state, detail, (d.get("MIN"), pts, reb, ast, val)
    return state, detail, None


print("=== RESULTS ===")
for player, gid, mkt, side, line in BETS:
    state, detail, r = result(gid, player, mkt)
    if not r:
        print(f"{player:16}: {state} ({detail})")
        continue
    mn, pts, reb, ast, val = r
    tag = ""
    if side:
        won = (val < line) if side == "Under" else (val > line)
        tag = f"  BET {side} {line} {mkt.upper()} -> {'WIN ✅' if won else 'LOSS ❌'}"
    print(f"{player:16}: FINAL — MIN {mn}, {pts:.0f}p/{reb:.0f}r/{ast:.0f}a  ({mkt.upper()}={val:.0f}){tag}")

print("\n=== captured line data (for CLV vs close) ===")
for f in ["xbet_snapshots.csv", "line_snapshots.csv"]:
    if os.path.exists(f):
        n = sum(1 for _ in open(f, encoding="utf-8")) - 1
        print(f"  {f}: {n} rows")
    else:
        print(f"  {f}: not present")
