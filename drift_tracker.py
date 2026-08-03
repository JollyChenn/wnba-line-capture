# drift_tracker.py - forward tracker for the DRIFT rules (the strongest structure found 2026-08-02).
# THE MECHANISM (validated league-wide, all signals pooled, n=271):
#   bets whose odds DRIFTED against us (no money came) : ROI -28.0%  t=-3.78   <- avoid / fade
#   bets whose odds SHORTENED on us  (money agreed)    : ROI +12.1%  t=+1.46   <- keep
# TWO TRACKED RULES:
#   A) SKIP-DRIFT   : the same bets we already log, minus any whose odds drifted >1% against us.
#   B) FADE-DRIFT   : bet the OPPOSITE side of a drifted UNDER, at the LATE (near-close) real price.
#      (verified implementable: late price 1.84 vs open 1.86, edge holds +22.1% vs +23.8%)
# Writes drift_track.csv (one row per graded bet, with bucket + both rules' returns) and prints a
# running scoreboard. Reads only existing files; safe to run any time; never fails the workflow.
import csv, os, sys, math, statistics, datetime
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return None
def RES(r): return (r.get("result") or "").upper()
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None
def gd(r):
    s = r.get("date", "")
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 else s

def main():
    # every pregame two-sided quote we captured
    Q = defaultdict(list)
    p = os.path.join(D, "xbet_board.csv")
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            t = ts(r["captured_utc"]); o = f(r["odds"])
            if not t or not o: continue
            if t.strftime("%H") >= "22" or t.strftime("%H") <= "04": continue   # pregame only
            Q[(t.strftime("%Y-%m-%d"), r["player"].lower(), r["market"], f(r["line"]), r["side"])].append((t, o))
    G = [r for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8"))
         if RES(r) in ("WIN", "LOSS")]
    def late_comp(r):                     # LATE complement quote = what you can actually bet
        other = "Over" if r["side"] == "Under" else "Under"
        q = sorted(Q.get((gd(r), r["player"].lower(), r["market"], f(r["line"]), other), []))
        return q[-1][1] if q else None
    rows = []
    for r in G:
        oc = f(r.get("odds_clv"))
        bucket = "n/a" if oc is None else ("drift" if oc < -0.01 else ("short" if oc > 0.01 else "steady"))
        as_bet = f(r.get("pnl")) or 0.0
        fade = ""
        if bucket == "drift":
            o = late_comp(r)
            if o: fade = round((o - 1) if RES(r) == "LOSS" else -1.0, 3)
        rows.append(dict(date=gd(r), player=r.get("player"), market=r.get("market"), side=r.get("side"),
                         line=r.get("line"), src=r.get("src"), result=RES(r), odds=r.get("odds"),
                         odds_clv=oc, bucket=bucket, as_bet=as_bet, fade_ret=fade,
                         skip_drift=("" if bucket == "drift" else as_bet)))
    w = csv.DictWriter(open(os.path.join(D, "drift_track.csv"), "w", newline="", encoding="utf-8"),
                       fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
    def st(v):
        v = [x for x in v if x != "" and x is not None]
        n = len(v)
        if n < 5: return f"n={n:>3} --"
        m = statistics.mean(v); s = statistics.pstdev(v)
        return f"n={n:>3} ROI={100*m:+5.1f}% P&L={m*n:+6.1f}u t={(m/(s/math.sqrt(n)) if s else 0):+.2f}"
    print("DRIFT TRACKER")
    print("  bucket returns (as-bet):")
    for b in ("drift", "steady", "short"):
        print(f"    {b:7}", st([x["as_bet"] for x in rows if x["bucket"] == b]))
    print("  RULE A skip-drift (all signals, drifted bets removed):")
    print("    ", st([x["skip_drift"] for x in rows]))
    print("    vs unfiltered:", st([x["as_bet"] for x in rows]))
    print("  RULE B fade-drift (bet opposite of drifted unders, LATE price):")
    print("    ", st([x["fade_ret"] for x in rows if x["src"] == "newunder"]))
    print("     all-signal version:", st([x["fade_ret"] for x in rows]))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
