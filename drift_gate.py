# drift_gate.py - LIVE SKIP-DRIFT GATE + FADE PAPER TRACKER (turned on 2026-08-02).
# Runs every capture cycle. For TODAY's signals it compares the FIRST captured price to the LATEST:
#   price got LONGER  (drift >=1%)  -> SKIP  (market walked away; these run -28% ROI, t=-3.78)
#                                    -> and log a FADE paper bet on the opposite side at the LATE price
#   price flat/SHORTER               -> CLEARED to bet (money agrees / neutral)
# Outputs:
#   drift_gate_today.csv  - today's verdict per bet (what to actually back)
#   fade_paper.csv        - append-only paper record of fade-drift bets (graded later by drift_tracker)
# Never fails the workflow (exit 0). stdlib only.
import csv, os, sys, datetime
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
DRIFT = 0.01          # >=1% longer = the market declined to back it
def f(x):
    try: return float(x)
    except Exception: return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

def main():
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    la = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    # our signals today, with their price series
    series = defaultdict(list)
    meta = {}
    p = os.path.join(D, "bets_log.csv")
    if not os.path.exists(p): print("no bets_log"); return
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r.get("date") not in (today, la): continue
        t = ts(r.get("captured_utc")); o = f(r.get("odds"))
        if not t or not o: continue
        k = (r["player"], r["market"], r["side"], r.get("line"))
        series[k].append((t, o)); meta[k] = r
    # the two-sided board, for the fade price
    board = defaultdict(list)
    bp = os.path.join(D, "xbet_board.csv")
    if os.path.exists(bp):
        for r in csv.DictReader(open(bp, encoding="utf-8")):
            if r["captured_utc"][:10] not in (today, la): continue
            t = ts(r["captured_utc"]); o = f(r["odds"])
            if t and o:
                board[(r["player"].lower(), r["market"], f(r["line"]), r["side"])].append((t, o))
    rows, fades = [], []
    for k, ser in series.items():
        ser.sort()
        first, last = ser[0][1], ser[-1][1]
        move = last / first - 1
        r = meta[k]
        drifted = move >= DRIFT
        verdict = "SKIP-drift" if drifted else ("BET (money agrees)" if move <= -DRIFT else "BET (steady)")
        fade_side = fade_price = ""
        if drifted:
            other = "Over" if r["side"] == "Under" else "Under"
            q = sorted(board.get((r["player"].lower(), r["market"], f(r.get("line")), other), []))
            if q:
                fade_side, fade_price = other, q[-1][1]
                fades.append([datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                              r.get("date"), r["player"], r["market"], other, r.get("line"), fade_price,
                              r.get("src"), round(move, 4)])
        rows.append([r.get("date"), r["player"], r["market"], r["side"], r.get("line"), r.get("src"),
                     first, last, round(100 * move, 1), verdict, fade_side, fade_price, len(ser)])
    hdr = ["date","player","market","side","line","src","open_odds","now_odds","move_pct","verdict","fade_side","fade_price","captures"]
    w = csv.writer(open(os.path.join(D, "drift_gate_today.csv"), "w", newline="", encoding="utf-8"))
    w.writerow(hdr); w.writerows(sorted(rows, key=lambda x: x[9]))
    # append fade paper bets, deduped on (date,player,market,side,line)
    fp = os.path.join(D, "fade_paper.csv")
    seen = set()
    if os.path.exists(fp):
        for r in csv.DictReader(open(fp, encoding="utf-8")):
            seen.add((r["date"], r["player"], r["market"], r["side"], r["line"]))
    new = [x for x in fades if (x[1], x[2], x[3], x[4], str(x[5])) not in seen]
    if new:
        isnew = not os.path.exists(fp)
        fh = open(fp, "a", newline="", encoding="utf-8"); fw = csv.writer(fh)
        if isnew: fw.writerow(["logged_utc","date","player","market","side","line","price","orig_src","orig_move"])
        fw.writerows(new); fh.close()
    nb = sum(1 for x in rows if x[9].startswith("BET"))
    ns = sum(1 for x in rows if x[9].startswith("SKIP"))
    print(f"drift gate {today}: {nb} CLEARED to bet, {ns} SKIPPED (drifted), +{len(new)} new fade paper bets")
    for x in sorted(rows, key=lambda x: x[9])[:12]:
        tag = "SKIP" if x[9].startswith("SKIP") else "BET "
        extra = f" -> FADE {x[10]} @ {x[11]}" if x[10] else ""
        print(f"  {tag} {x[1][:18]:18} {x[2]} {x[3]} {x[4]:>5} {x[6]}->{x[7]} ({x[8]:+.1f}%) [{x[5]}]{extra}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
