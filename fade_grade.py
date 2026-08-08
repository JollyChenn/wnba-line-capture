# fade_grade.py - grades the FADE-DRIFT paper record (fade_paper.csv) against real box scores.
# This is the FORWARD proof-of-concept for the fade rule: bets logged BEFORE the games, at the real
# late price, graded after. Unlike the backtest, none of this data was used to discover the rule.
# Writes fade_graded.csv + prints the running forward scoreboard (the number that decides go-live).
import csv, os, sys, math, statistics
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return None

def _plus(dd, n):
    """YYYY-MM-DD + n days, as a string (dates here are strings, not datetimes)."""
    import datetime as _dt
    return (_dt.date.fromisoformat(dd) + _dt.timedelta(days=n)).isoformat()

def main():
    fp = os.path.join(D, "fade_paper.csv")
    if not os.path.exists(fp): print("no fade_paper.csv yet"); return
    # actuals from the elo box history (refreshed nightly by predict-tonight)
    # Read BOTH box sources. elo_model/box_full.csv is the deep multi-season history but it is only
    # refreshed by the elo crawl (stale at 2026-08-02), while data/box_2026.csv is refreshed nightly
    # by daily_picks (current through 2026-08-07). Reading only the elo copy silently froze fade
    # grading 5 days behind - the fades were never graded, so the record looked like "n=2" forever.
    gd, act = {}, {}
    for _g, _b in ((os.path.join(D, "elo_model", "games_full.csv"), os.path.join(D, "elo_model", "box_full.csv")),
                   (os.path.join(D, "data", "games_2026.csv"),     os.path.join(D, "data", "box_2026.csv"))):
        if not (os.path.exists(_g) and os.path.exists(_b)): continue
        for g in csv.DictReader(open(_g, encoding="utf-8")):
            gd[g["game_id"]] = g["date"]
        for r in csv.DictReader(open(_b, encoding="utf-8")):
            d = gd.get(r["game_id"], "")
            if not d: continue
            dd = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            pts, reb, ast = f(r["pts"]) or 0, f(r["reb"]) or 0, f(r["ast"]) or 0
            act[(dd, r["player"].lower())] = {"pts": pts, "reb": reb, "ast": ast, "pra": pts+reb+ast,
                                              "pr": pts+reb, "pa": pts+ast, "ra": reb+ast}
    # SLATE DATE != GAME DATE. fade_paper.csv stamps the date the bet was LOGGED, but a line captured
    # late in the UTC day belongs to a game that tips the next calendar day. Matching the box on the
    # slate date exactly left 13 of 15 fades permanently ungraded (Chelsea Gray logged 08-02, played
    # 08-01 and 08-03). Take the player's first game within +2 days of the slate instead.
    by_player = {}
    for (dd, plow), v in act.items():
        by_player.setdefault(plow, []).append((dd, v))
    for v in by_player.values(): v.sort()
    def actual_for(slate, plow):
        exact = act.get((slate, plow))
        if exact: return exact
        for dd, v in by_player.get(plow, ()):
            if slate <= dd <= _plus(slate, 2): return v
        return None
    rows, rets = [], []
    for r in csv.DictReader(open(fp, encoding="utf-8")):
        a = (actual_for(r["date"], r["player"].lower()) or {}).get(r["market"])
        ln, pr = f(r["line"]), f(r["price"])
        if a is None or ln is None or pr is None:
            rows.append({**r, "actual": "", "result": "", "ret": ""}); continue
        if a == ln:
            rows.append({**r, "actual": a, "result": "push", "ret": 0}); continue
        win = (a > ln) if r["side"] == "Over" else (a < ln)
        ret = round((pr - 1) if win else -1.0, 3)
        rows.append({**r, "actual": a, "result": "WIN" if win else "loss", "ret": ret})
        rets.append(ret)
    if rows:
        w = csv.DictWriter(open(os.path.join(D, "fade_graded.csv"), "w", newline="", encoding="utf-8"),
                           fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    n = len(rets)
    print(f"FADE-DRIFT FORWARD PAPER: {len(rows)} logged, {n} settled")
    if n >= 3:
        wins = sum(1 for r in rows if r["result"] == "WIN")
        m = statistics.mean(rets); s = statistics.pstdev(rets)
        t = m/(s/math.sqrt(n)) if s else 0
        print(f"  {wins}-{n-wins} ({100*wins/n:.0f}%) ROI={100*m:+.1f}% P&L={m*n:+.1f}u t={t:+.2f}")
        print(f"  GO-LIVE GATE: need n>=100 with ROI>+10% (backtest said +23.5%) — {n}/100 collected")
    for r in rows[-6:]:
        print(f"   {r['date']} {r['player'][:18]:18} {r['market']} {r['side']} {r['line']:>5} @ {r['price']} -> {r.get('result','pending')}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
