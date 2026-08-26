# TRACK 3 step 9: (a) paired follow-vs-fade within game; (b) per-family INDEPENDENT CLV from xbet_board;
# (c) CLV-vs-ROI quadrant using the independent numbers.
import csv, os, sys, math, statistics, collections, random, datetime, pickle
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"

def ts(s):
    s = (s or "").replace("Z", "+00:00")
    try:
        d = datetime.datetime.fromisoformat(s); return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)
    except Exception: return None

# ---------- (a) paired follow vs fade ----------
FULL = {"Atlanta Dream": "ATL", "Chicago Sky": "CHI", "Connecticut Sun": "CON", "Dallas Wings": "DAL",
        "Golden State Valkyries": "GS", "Indiana Fever": "IND", "Los Angeles Sparks": "LA",
        "Las Vegas Aces": "LV", "Minnesota Lynx": "MIN", "New York Liberty": "NY",
        "Phoenix Mercury": "PHX", "Portland Fire": "POR", "Seattle Storm": "SEA",
        "Toronto Tempo": "TOR", "Washington Mystics": "WSH"}
def am2dec(a):
    a = float(a); return 1 + (a / 100 if a > 0 else 100 / -a)
GM = list(csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")))
res = {}
for g in GM:
    try: hs, a = float(g["home_score"]), float(g["away_score"])
    except Exception: continue
    res[(g["home"], g["away"], g["date"])] = (hs, a, ts(g["tip"]))
raw = collections.defaultdict(list); meta = {}
for r in csv.DictReader(open(os.path.join(D, "gamelines.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    pr = r["prices"].split(",")
    if len(pr) != 2: continue
    try: d1, d2 = am2dec(pr[0]), am2dec(pr[1])
    except Exception: continue
    raw[r["matchup_id"]].append((t, r["type"], r.get("points", ""), d1, d2))
    meta[r["matchup_id"]] = (r["teams"], ts(r["start"]))
def mainpick(c): return min(c, key=lambda x: abs(1 / x[3] - 1 / x[4])) if c else None
pairs = {"sp": [], "to": []}
for mid, rows in raw.items():
    teams, start = meta[mid]
    try: h, a = [FULL[x] for x in teams.split("|")]
    except Exception: continue
    bt = collections.defaultdict(list)
    for x in rows: bt[x[0]].append(x)
    snaps = []
    for t in sorted(bt):
        g = bt[t]
        sp = mainpick([x for x in g if x[1] == "spread" and x[2]])
        to = mainpick([x for x in g if x[1] == "total" and x[2]])
        snaps.append(dict(t=t, sp=(float(sp[2]), sp[3], sp[4]) if sp else None,
                          to=(float(to[2]), to[3], to[4]) if to else None))
    key = None
    for dd in ((start - datetime.timedelta(hours=6)).strftime("%Y%m%d"), start.strftime("%Y%m%d")):
        if (h, a, dd) in res: key = (h, a, dd); break
        if (a, h, dd) in res: key = (a, h, dd); break
    if not key: continue
    hs, aw, tip = res[key]
    if key[0] != h: hs, aw = aw, hs
    for f in ("sp", "to"):
        A = [x for x in snaps if x[f]]
        B = [x for x in snaps if x[f] and x["t"] < tip - datetime.timedelta(hours=6)]
        if not A or not B: continue
        mv = B[-1][f][0] - A[0][f][0]
        ln, o1, o2 = B[-1][f]
        if f == "sp":
            cov = (hs - aw) + ln
            if cov == 0: continue
            p1 = (o1 - 1) if cov > 0 else -1.0; p2 = (o2 - 1) if cov < 0 else -1.0
            s1 = mv < 0
        else:
            d = (hs + aw) - ln
            if d == 0: continue
            p1 = (o1 - 1) if d > 0 else -1.0; p2 = (o2 - 1) if d < 0 else -1.0
            s1 = mv > 0
        pairs[f].append((abs(mv), (p1 if s1 else p2) - (p2 if s1 else p1)))
print("=== (a) PAIRED follow-minus-fade, same game, same instant (removes all game-level noise) ===")
for f, nm in (("sp", "spread"), ("to", "total")):
    for thr in (0.5, 1.0, 1.5):
        v = [d for m, d in pairs[f] if m >= thr]
        if len(v) < 20: continue
        m_ = statistics.mean(v); se = statistics.stdev(v) / math.sqrt(len(v))
        t = m_ / se
        NP = 20000; c = 0
        for _ in range(NP):
            s = sum(x if random.random() < .5 else -x for x in v) / len(v)
            if s >= m_: c += 1
        print("  %-7s |move|>=%.1f  n=%3d games  follow-fade = %+6.1f%% [%+6.1f,%+6.1f]  t=%+.2f  sign-flip p=%.4f" % (
            nm, thr, len(v), m_ * 100, (m_ - 1.96 * se) * 100, (m_ + 1.96 * se) * 100, t, (c + 1) / (NP + 1)))

# ---------- (b) independent CLV from xbet_board, per family ----------
tipof = {g["game_id"]: ts(g["tip"]) for g in GM}; dateof = {g["game_id"]: g["date"] for g in GM}
pl_game = {}
for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
    if r["game_id"] in dateof: pl_game[(r["player"].lower(), dateof[r["game_id"]])] = r["game_id"]
Q = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(D, "xbet_board.csv"), encoding="utf-8")):
    t = ts(r["captured_utc"])
    if not t: continue
    try: Q[(r["player"].lower(), r["market"])].append((t, float(r["line"]), r["side"], float(r["odds"])))
    except Exception: pass
for k in Q: Q[k].sort()
def snaps(p, m, tip, hours=72):
    lo = tip - datetime.timedelta(hours=hours)
    d = collections.defaultdict(dict)
    for t, ln, s, o in Q.get((p, m), ()):
        if lo < t < tip: d[(t, ln)][s] = o
    return sorted((k[0], k[1], v["Over"], v["Under"]) for k, v in d.items() if "Over" in v and "Under" in v)
def vf(o, u, side):
    a, b = 1 / o, 1 / u; s = a + b
    return (a / s) if side == "Over" else (b / s)

rows = []
for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8")):
    if r["result"] not in ("WIN", "loss"): continue
    p, m, side = r["player"].lower(), r["market"], r["side"]
    gid = pl_game.get((p, r["date"]))
    if not gid: continue
    tip = tipof[gid]
    S = snaps(p, m, tip)
    if not S: continue
    oline, oodds = float(r["line"]), float(r["odds"])
    same = [x for x in S if abs(x[1] - oline) < 1e-6]
    tc = S[-1]
    ind_line_clv = (tc[1] - oline) if side == "Over" else (oline - tc[1])
    ind_odds_clv = (oodds / (same[-1][2] if side == "Over" else same[-1][3]) - 1) if same else None
    ev_close = (vf(same[-1][2], same[-1][3], side) * oodds - 1) if same else None
    rows.append(dict(gid=gid, src=r["src"], side=side, market=m, pnl=float(r["pnl"]),
                     stored_odds=(float(r["odds_clv"]) if r["odds_clv"] else None),
                     stored_line=(float(r["line_clv"]) if r["line_clv"] else None),
                     ind_odds=ind_odds_clv, ind_line=ind_line_clv, ev_close=ev_close,
                     lag=(tip - tc[0]).total_seconds() / 3600))
print("\n=== (b) INDEPENDENT CLV RECOMPUTE FROM xbet_board -- per family ===")
print("  ind_line = true last pre-tip 1xbet line minus our line (signed our way); ind_odds = our price / last price at OUR line - 1")
print("  ev_close = our price x vig-free P(our side) implied by the last two-sided quote at OUR line, minus 1")
def bb(vals, nb=4000):
    b = list(vals.values())
    if len(b) < 3: return (float("nan"),) * 3 + (0,)
    allv = [x for q in b for x in q]; ms = []
    for _ in range(nb):
        s = [random.choice(b) for _ in range(len(b))]; fl = [x for q in s for x in q]; ms.append(sum(fl) / len(fl))
    ms.sort(); return statistics.mean(allv), ms[int(.025 * nb)], ms[int(.975 * nb)], len(allv)
def grp(rs, key):
    d = collections.defaultdict(list)
    for r in rs:
        if r[key] is not None: d[r["gid"]].append(r[key])
    return d
fams = collections.defaultdict(list)
for r in rows: fams[r["src"]].append(r)
print("  %-12s %6s %6s | %11s %8s | %10s %8s | %11s %8s | %9s" % (
    "family", "n", "games", "storedODDS%", "indODDS%", "storedLINE", "indLINE", "EVvsClose%", "beat%", "ROI%"))
for name, rs in [("ALL", rows)] + sorted(fams.items(), key=lambda kv: -len(kv[1])):
    so = bb(grp(rs, "stored_odds")); io = bb(grp(rs, "ind_odds"))
    sl = bb(grp(rs, "stored_line")); il = bb(grp(rs, "ind_line"))
    ev = bb(grp(rs, "ev_close")); ro = bb(grp(rs, "pnl"))
    evv = [r["ev_close"] for r in rs if r["ev_close"] is not None]
    beat = (sum(1 for x in evv if x > 0) / len(evv) * 100) if evv else float("nan")
    print("  %-12s %6d %6d | %+11.2f %+8.2f | %+10.2f %+8.2f | %+11.2f %7.1f%% | %+9.1f" % (
        name, len(rs), len(set(r["gid"] for r in rs)), so[0] * 100, io[0] * 100, sl[0], il[0], ev[0] * 100, beat, ro[0] * 100))
print("\n  stored vs independent LINE-CLV disagreement: mean stored %+.3f vs independent %+.3f pts" % (
    statistics.mean([r["stored_line"] for r in rows if r["stored_line"] is not None]),
    statistics.mean([r["ind_line"] for r in rows])))
d = [(r["stored_line"], r["ind_line"]) for r in rows if r["stored_line"] is not None]
print("  exact agreement on line-CLV: %d/%d (%.1f%%)" % (
    sum(1 for a, b in d if abs(a - b) < 1e-9), len(d), sum(1 for a, b in d if abs(a - b) < 1e-9) / len(d) * 100))
print("  true last 1xbet quote is a median %.2fh before tip -- the 'close' is not a close" % statistics.median([r["lag"] for r in rows]))
with open(os.path.join(D, "outputs", "clv", "indep_rows.pkl"), "wb") as f: pickle.dump(rows, f)
