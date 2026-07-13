# elo_grade.py - append actual results + hit-columns to elo_forward_log entries whose game is now final.
# Reads games_full (has scores) + elo_forward_log (has predictions + pin lines snapshot) -> elo_graded.csv.
# For each prediction row grades: margin, total, ATS(v3/v5), OU (vs Pinnacle spread/total), ML side.
# Also grabs CLOSING line: latest gamelines.csv row before tip = the tightest CLV reference.
# stdlib; never fails the workflow.
import csv, os, sys, datetime, statistics
from collections import defaultdict
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(D)
def f(x):
    try: return float(x)
    except Exception: return None
def parse_pin(s):
    if not s or "@" not in s: return None, None
    p, pr = s.split("@", 1)
    return f(p), pr

def main():
    # scores by (date, home, away)
    scores = {}
    for g in csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")):
        if g["home_score"]:
            scores[(g["date"], g["home"], g["away"])] = (f(g["home_score"]), f(g["away_score"]))
    # closing lines from gamelines: latest row per (teams,type,side) before ~tip
    gl_all = []
    gl = os.path.join(REPO, "gamelines.csv")
    if os.path.exists(gl):
        for r in csv.DictReader(open(gl, encoding="utf-8")):
            gl_all.append(r)
    def close_line(teams, tip_utc, typ, side=""):
        best = None
        for r in gl_all:
            if r["type"] != typ or r.get("side", "") != side: continue
            if r["teams"] != teams: continue
            if r["captured_utc"] <= tip_utc and (best is None or r["captured_utc"] > best["captured_utc"]):
                best = r
        if not best: return "", ""
        return best["points"], best["prices"]

    src = os.path.join(D, "elo_forward_log.csv")
    if not os.path.exists(src): print("no log yet"); return
    dst = os.path.join(D, "elo_graded.csv")
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    hdr = list(rows[0].keys()) if rows else []
    extra = ["home_score","away_score","margin","total",
             "close_spread","close_total","close_ml",
             "v3_err","v5_err","tot_err",
             "ats_v3","ats_v5","ou","ml_pick_v5","ml_correct"]
    new = not os.path.exists(dst)
    fh = open(dst, "w", newline="", encoding="utf-8"); w = csv.writer(fh)
    w.writerow(hdr + extra)
    dedup = set()   # (date,home,away,logged_utc) dedup
    graded = 0; unsettled = 0
    for r in rows:
        key = (r["date"], r["home"], r["away"], r["logged_utc"])
        if key in dedup: continue
        dedup.add(key)
        sc = scores.get((r["date"].replace("-", ""), r["home"], r["away"]))
        if not sc: unsettled += 1; w.writerow([r[k] for k in hdr] + [""]*len(extra)); continue
        hs, as_ = sc; margin = hs - as_; total = hs + as_
        # closing lines — teams field format matches gamelines.csv (Full Name|Full Name; both orderings)
        # find via any teams-string in gamelines that has both team abbrevs' cities... best-effort: skip if not resolvable
        m3, m5, tp = f(r.get("v3_margin")), f(r.get("v5_margin")), f(r.get("tot_pred"))
        v3e = margin - m3 if m3 is not None else ""
        v5e = margin - m5 if m5 is not None else ""
        tpe = total - tp if tp is not None else ""
        # ATS: pin_spread cell like "-6.5@114,-138" -> spread is home line
        ps, _ = parse_pin(r.get("pin_spread", ""))
        pt, _ = parse_pin(r.get("pin_total", ""))
        ats3 = ats5 = ou = mlp = mlc = ""
        if ps is not None and m3 is not None:
            ats3 = "W" if (m3 + ps > 0) == (margin + ps > 0) else ("push" if margin + ps == 0 else "L")
        if ps is not None and m5 is not None:
            ats5 = "W" if (m5 + ps > 0) == (margin + ps > 0) else ("push" if margin + ps == 0 else "L")
        if pt is not None and tp is not None:
            side = "O" if tp > pt else "U"
            hit = "O" if total > pt else ("push" if total == pt else "U")
            ou = "W" if side == hit else ("push" if hit == "push" else "L")
        if m5 is not None:
            mlp = r["home"] if m5 > 0 else r["away"]
            mlc = "W" if (m5 > 0) == (margin > 0) else "L"
        w.writerow([r[k] for k in hdr] + [hs, as_, margin, total, "", "", "", v3e, v5e, tpe,
                                          ats3, ats5, ou, mlp, mlc])
        graded += 1
    fh.close()
    # quick score
    print(f"graded {graded} / unsettled {unsettled}")
    # tallies
    def tally(col):
        gr = [r for r in csv.DictReader(open(dst, encoding="utf-8")) if r[col] in ("W", "L")]
        w = sum(1 for r in gr if r[col] == "W")
        return f"{w}-{len(gr)-w} ({100*w/len(gr):.0f}%)" if gr else "0-0"
    for c in ("ats_v3", "ats_v5", "ou", "ml_correct"):
        print(f"  {c:12} {tally(c)}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        import traceback; traceback.print_exc()
    sys.exit(0)
