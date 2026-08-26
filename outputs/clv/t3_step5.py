# TRACK 3 step 5: MODEL S vs the CLOSING PROP LINE (brief section 42).
# Population = shadow_forward.csv config=MODEL_S (the project's own Model S record) + model_forward.csv (live).
# For every bet: closing 1xbet two-sided quote before tip -> vig-free P(our side) -> expected wins vs actual wins.
import csv, os, sys, math, statistics, collections, random, datetime, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"

def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None

GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
tipof = {g["game_id"]: ts(g["tip"]) for g in GM}
dateof = {g["game_id"]: g["date"] for g in GM}
pl_game = {}
for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
    if r["game_id"] in dateof:
        pl_game[(r["player"].lower(), dateof[r["game_id"]])] = r["game_id"]

Q = collections.defaultdict(list)           # (player,market) -> [(t,line,side,odds)]
for r in csv.DictReader(open(os.path.join(D, "xbet_board.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    try: Q[(r["player"].lower(), r["market"])].append((t, float(r["line"]), r["side"], float(r["odds"])))
    except Exception: pass
for k in Q: Q[k].sort()

PS = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "pinn_snapshots.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    try: ln = float(r["pinn_line"]); fa = float(r["pinn_fair"])
    except Exception: continue
    if t: PS[(r["player"].lower(), r["market"], r["side"], ln)].append((t, fa))
for k in PS: PS[k].sort()


def closing(p, m, tip, hours=72):
    """last two-sided 1xbet snapshot before tip -> (t, line, over_odds, under_odds)"""
    lo = tip - datetime.timedelta(hours=hours)
    q = [x for x in Q.get((p, m), ()) if lo < x[0] < tip]
    if not q: return None
    snap = collections.defaultdict(dict)
    for t, ln, s, o in q: snap[(t, ln)][s] = o
    ok = [(k[0], k[1], v["Over"], v["Under"]) for k, v in snap.items() if "Over" in v and "Under" in v]
    if not ok: return None
    ok.sort()
    return ok[-1]


def quote_at(p, m, tip, line, when, hours=72):
    lo = tip - datetime.timedelta(hours=hours)
    q = [x for x in Q.get((p, m), ()) if lo < x[0] <= when and abs(x[1] - line) < 1e-6]
    if not q: return None
    snap = collections.defaultdict(dict)
    for t, ln, s, o in q: snap[t][s] = o
    ok = [(t, v["Over"], v["Under"]) for t, v in snap.items() if "Over" in v and "Under" in v]
    if not ok: return None
    ok.sort(); return ok[-1]


def vf(over, under, side):
    a, b = 1 / over, 1 / under; s = a + b
    return (a / s) if side == "Over" else (b / s)


# ---------- load Model S populations ----------
def load_shadow():
    out = []
    for r in csv.DictReader(open(os.path.join(D, "shadow_forward.csv"), encoding="utf-8")):
        if r["config"] != "MODEL_S": continue
        if r["result"] not in ("WIN", "loss"): continue
        d = r["slate"].replace("-", "")
        out.append(dict(date=d, player=r["player"], market=r["market"], side="Over",
                        line=float(r["line"]), odds=float(r["odds"] or 0), src=r["src"],
                        prev=r.get("prev_line", ""), result=r["result"],
                        actual=float(r["actual"]) if r["actual"] else None,
                        logged=ts(r["logged_utc"]), pop="shadow_MODEL_S"))
    return out

def load_live():
    out = []
    for r in csv.DictReader(open(os.path.join(D, "model_forward.csv"), encoding="utf-8")):
        if r["result"] not in ("WIN", "loss"): continue
        out.append(dict(date=r["slate"], player=r["player"], market=r["market"], side=r["side"],
                        line=float(r["line"]), odds=float(r["odds"]), src=r["src"],
                        prev=r.get("prev_line", ""), result=r["result"],
                        actual=float(r["actual"]) if r["actual"] else None,
                        logged=ts(r["tip"]), pop="live_model_forward"))
    return out

pops = {"shadow MODEL_S": load_shadow(), "live model_forward": load_live()}

# also a Model-S-shaped slice of graded_bets (over, pra/pr/pts, src in flip/hotover/overshoot)
GB = []
for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")):
    if r["result"] not in ("WIN", "loss"): continue
    if r["side"] != "Over": continue
    if r["market"] not in ("pra", "pr", "pts"): continue
    if r["src"] not in ("flip", "flip_paper", "hotover", "overshoot"): continue
    GB.append(dict(date=r["date"], player=r["player"], market=r["market"], side="Over",
                   line=float(r["line"]), odds=float(r["odds"]), src=r["src"], prev="",
                   result=r["result"], actual=float(r["actual"]), logged=None, pop="graded_ModelS_shape"))
pops["graded Model-S-shape"] = GB


def bboot(vals_by_block, nb=4000):
    b = list(vals_by_block.values())
    if len(b) < 3: return (float("nan"),) * 3
    allv = [x for q in b for x in q]; pt = statistics.mean(allv); ms = []
    for _ in range(nb):
        s = [random.choice(b) for _ in range(len(b))]
        fl = [x for q in s for x in q]; ms.append(sum(fl) / len(fl))
    ms.sort(); return pt, ms[int(.025 * nb)], ms[int(.975 * nb)]


print("=" * 100)
print("SECTION 42 TEST: do Model S overs beat what the CLOSING 1xbet prop line implies?")
print("  expected wins = sum of vig-free P(over) from the LAST two-sided 1xbet quote before tip")
print("=" * 100)
allrows = {}
for name, rs in pops.items():
    n_tot = len(rs); matched = []
    for r in rs:
        gid = pl_game.get((r["player"].lower(), r["date"]))
        if not gid: continue
        tip = tipof[gid]
        cl = closing(r["player"].lower(), r["market"], tip)
        if not cl: continue
        ct, cline, co, cu = cl
        p_close_at_close_line = vf(co, cu, r["side"])
        # translate to OUR line: need the closing two-sided quote AT OUR LINE if it exists
        lo = tip - datetime.timedelta(hours=72)
        q = [x for x in Q.get((r["player"].lower(), r["market"]), ()) if lo < x[0] < tip and abs(x[1] - r["line"]) < 1e-6]
        snap = collections.defaultdict(dict)
        for t, ln, s, o in q: snap[t][s] = o
        ok = sorted([(t, v["Over"], v["Under"]) for t, v in snap.items() if "Over" in v and "Under" in v])
        p_close_our_line = vf(ok[-1][1], ok[-1][2], r["side"]) if ok else None
        won = 1 if r["result"] == "WIN" else 0
        matched.append(dict(r, gid=gid, tip=tip, cl_t=ct, cl_line=cline, cl_over=co, cl_under=cu,
                            p_close_line=p_close_at_close_line, p_close_ours=p_close_our_line,
                            won=won, lag=(tip - ct).total_seconds() / 3600,
                            line_move=(cline - r["line"]) if r["side"] == "Over" else (r["line"] - cline)))
    allrows[name] = matched
    if not matched:
        print("\n%-22s no rows matched to a closing quote" % name); continue
    gb = collections.defaultdict(list)
    for m in matched: gb[m["gid"]].append(m["won"])
    w = sum(m["won"] for m in matched); n = len(matched)
    exp_l = [m["p_close_ours"] for m in matched if m["p_close_ours"] is not None]
    print("\n--- %s ---   settled=%d  matched to closing quote=%d  independent games=%d" % (
        name, n_tot, n, len(gb)))
    ph = bboot(gb)
    print("    actual hit-rate           %5.1f%% [%5.1f,%5.1f]  (%d/%d)" % (ph[0] * 100, ph[1] * 100, ph[2] * 100, w, n))
    if exp_l:
        sub = [m for m in matched if m["p_close_ours"] is not None]
        gb2 = collections.defaultdict(list)
        for m in sub: gb2[m["gid"]].append(m["won"] - m["p_close_ours"])
        d = bboot(gb2)
        gb3 = collections.defaultdict(list)
        for m in sub: gb3[m["gid"]].append(m["won"])
        pa = bboot(gb3)
        print("    CLOSING line implies      %5.1f%%   (at OUR line, vig-free, n=%d)" % (statistics.mean(exp_l) * 100, len(exp_l)))
        print("    actual on that subset     %5.1f%%" % (pa[0] * 100))
        print("    BEAT-THE-CLOSE delta      %+5.1f pp [%+5.1f,%+5.1f]   <- section 42 statistic" % (d[0] * 100, d[1] * 100, d[2] * 100))
        # permutation: shuffle wins within game blocks against p_close
        obs = statistics.mean([m["won"] - m["p_close_ours"] for m in sub])
        blocks = collections.defaultdict(list)
        for m in sub: blocks[m["gid"]].append(m)
        NP = 4000; cnt = 0
        for _ in range(NP):
            keys = list(blocks.keys()); vals = [[x["won"] for x in blocks[k]] for k in keys]
            random.shuffle(vals); tot = []
            for k, v in zip(keys, vals):
                rs = blocks[k]; vv = (v * ((len(rs) // len(v)) + 1))[:len(rs)]
                for rr, x in zip(rs, vv): tot.append(x - rr["p_close_ours"])
            if statistics.mean(tot) >= obs: cnt += 1
        print("    game-block permutation p  %.4f" % ((cnt + 1) / (NP + 1)))
    lm = [m["line_move"] for m in matched]
    print("    1xbet line move open->close (our-side favourable = +): mean %+.3f pts, median %+.2f, unchanged %.0f%%" % (
        statistics.mean(lm), statistics.median(lm), sum(1 for x in lm if abs(x) < 1e-6) / len(lm) * 100))
    print("    closing quote captured median %.2fh before tip" % statistics.median([m["lag"] for m in matched]))
    if r["odds"]:
        pnl = [(m["odds"] - 1) if m["won"] else -1.0 for m in matched if m["odds"]]
        gbp = collections.defaultdict(list)
        for m in matched:
            if m["odds"]: gbp[m["gid"]].append((m["odds"] - 1) if m["won"] else -1.0)
        rr = bboot(gbp)
        print("    realised ROI              %+5.1f%% [%+5.1f,%+5.1f]  n=%d" % (rr[0] * 100, rr[1] * 100, rr[2] * 100, len(pnl)))

with open(os.path.join(D, "outputs", "clv", "models_rows.pkl"), "wb") as f:
    pickle.dump({k: [{kk: (vv.isoformat() if isinstance(vv, datetime.datetime) else vv) for kk, vv in r.items()} for r in v] for k, v in allrows.items()}, f)
