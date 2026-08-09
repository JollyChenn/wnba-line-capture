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
    p = os.path.join(D, "bets_log.csv")
    if not os.path.exists(p): print("no bets_log"); return
    alld = {r.get("date") for r in csv.DictReader(open(p, encoding="utf-8")) if r.get("date")}
    want = {today, la}
    if not (want & alld):          # quiet window (between slates) -> show the most recent slate instead
        want = {max(alld)} if alld else set()
        print(f"[no captures yet for {today}; showing most recent slate {max(alld) if alld else '-'}]")
    # our signals for the target slate, with their price series
    series = defaultdict(list)
    meta = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r.get("date") not in want: continue
        t = ts(r.get("captured_utc")); o = f(r.get("odds"))
        if not t or not o: continue
        # key WITHOUT the line: a line move (21% of bets) must not look like a brand-new bet with no history
        k = (r["player"], r["market"], r["side"])
        series[k].append((t, f(r.get("line")), o)); meta[k] = r
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
        cur_line = ser[-1][1]                       # the line the book is offering NOW
        opened_line = ser[0][1]
        line_moved = (opened_line is not None and cur_line is not None
                      and abs(cur_line - opened_line) >= 0.25)
        # odds drift is only meaningful WITHIN one line — measure it on the current line's captures
        cl = [x for x in ser if x[1] == cur_line]
        first, last = cl[0][2], cl[-1][2]
        move = last / first - 1
        r = dict(meta[k]); r["line"] = cur_line     # always quote the CURRENT line, not the stale one
        drifted = move >= DRIFT
        verdict = "SKIP-drift" if drifted else ("BET (money agrees)" if move <= -DRIFT else "BET (steady)")
        # CONFIDENCE: how often a read this shape is still final at tip (measured at T-8h on 670 bets).
        # Lets you bet at bedtime instead of 3am: strong money-on-us is 93% locked in already.
        if len(cl) < 2:     conf = "NO READ (new line)"  # line just moved / first capture: no odds history yet
        elif move <= -0.03: conf = "BET NOW 93%"       # money already piled on our side - rarely reverses
        elif move < -0.005: conf = "bet now 81%"
        elif move < DRIFT:  conf = "ok 85%"            # flat: no news either way
        else:               conf = "WAIT 70%"          # early drift is the LEAST stable read - confirm late
        fade_side = fade_price = ""
        if drifted:
            other = "Over" if r["side"] == "Under" else "Under"
            q = sorted(board.get((r["player"].lower(), r["market"], cur_line, other), []))
            if q:
                fade_side, fade_price = other, q[-1][1]
                fades.append([datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                              r.get("date"), r["player"], r["market"], other, r.get("line"), fade_price,
                              r.get("src"), round(move, 4)])
        lm = f"{opened_line}->{cur_line}" if line_moved else ""
        # SPAN, not just count, is what makes a drift read meaningful: 4 captures crammed into 20
        # minutes tell you nothing, while 3 spread over 4 hours is a real window for the book to
        # reprice. Emitting it lets the alert vet on elapsed time instead of a raw tally.
        span_h = round((cl[-1][0] - cl[0][0]).total_seconds() / 3600, 1) if len(cl) > 1 else 0.0
        rows.append([r.get("date"), r["player"], r["market"], r["side"], cur_line, r.get("src"),
                     first, last, round(100 * move, 1), verdict, conf, lm, fade_side, fade_price,
                     len(cl), span_h])
    hdr = ["date","player","market","side","line","src","open_odds","now_odds","move_pct","verdict","confidence","line_moved","fade_side","fade_price","captures","span_h"]
    w = csv.writer(open(os.path.join(D, "drift_gate_today.csv"), "w", newline="", encoding="utf-8"))
    w.writerow(hdr); w.writerows(sorted(rows, key=lambda x: x[9]))
    # ---- PERMANENT RECORD ---------------------------------------------------------------------
    # drift_gate_today.csv is overwritten every run, so the reads that led to a bet were being lost
    # the moment the slate rolled. drift_log.csv is append-only: one row each time a bet's read
    # actually CHANGES (new price, new line, more checks). That's what lets us ask later whether the
    # drift read separated winners from losers, instead of just believing it does.
    lp = os.path.join(D, "drift_log.csv")
    last = {}
    if os.path.exists(lp):
        for r in csv.DictReader(open(lp, encoding="utf-8")):
            last[(r["date"], r["player"], r["market"], r["side"])] = (r["line"], r["now_odds"], r["captures"])
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = [x for x in rows
               if last.get((str(x[0]), x[1], x[2], x[3])) != (str(x[4]), str(x[7]), str(x[14]))]
    if changed:
        isnew = not os.path.exists(lp)
        fh = open(lp, "a", newline="", encoding="utf-8"); fw = csv.writer(fh)
        if isnew: fw.writerow(["logged_utc"] + hdr)
        fw.writerows([[stamp] + x for x in changed]); fh.close()
    print(f"drift_log: +{len(changed)} read(s)")
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
        extra = f" -> FADE {x[12]} @ {x[13]}" if x[12] else ""
        lmv = f" LINE {x[11]}" if x[11] else ""
        print(f"  {tag} {x[1][:18]:18} {x[2]} {x[3]} {x[4]:>5} {x[6]}->{x[7]} ({x[8]:+.1f}%) [{x[10]}]{lmv} [{x[5]}]{extra}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
