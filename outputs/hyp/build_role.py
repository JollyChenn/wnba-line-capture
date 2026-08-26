# build_role.py - one dataset for BOTH hypotheses. Writes outputs/hyp/role_rows.json.
# Every feature uses ONLY games strictly BEFORE the game being predicted, and only games
# played for the player's CURRENT team.
import os, sys, json, statistics, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L

g = L.boot()
pgrow, hist, roster, gmeta = g["pgrow"], g["hist"], g["roster"], g["gmeta"]
teamuse, side, prevline, teamof = g["teamuse"], g["side"], g["prevline"], g["teamof"]
ALL_MK = g["ALL_MK"]; _pl = g["_pl"]; load = g["load"]; ts = g["ts"]

# ---- which board names only join because of today's namefix? (for the censorship A/B) ----
import csv
NEWLY = set()
seen = set()
for b in load("xbet_board.csv"):
    nm = (b.get("player") or "").strip()
    if nm in seen: continue
    seen.add(nm)
    r = _pl(nm)
    if r != nm.lower() and r in teamof:
        NEWLY.add(r)
print("players resolved ONLY by today's name fix (%d): %s" % (len(NEWLY), sorted(NEWLY)))

# ---- per-(player,tip) prior history on the CURRENT team ----
def prior_ct(pl, tm, gt):
    return [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == tm]

# ---- usage / scoring rank inside her own team, from prior games only ----
RANKC = {}
def ranks_for(tm, gt):
    key = (tm, gt)
    if key in RANKC: return RANKC[key]
    pool = {}
    for m in roster.get((tm, gt), ()):
        pv = prior_ct(m, tm, gt)
        if len(pv) < 3: continue
        last = pv[-10:]
        pool[m] = (statistics.mean(x["use"] for x in last),
                   statistics.mean(x["pts"] for x in last),
                   statistics.mean(x["min"] for x in last), len(pv))
    ur = {m: i+1 for i, m in enumerate(sorted(pool, key=lambda m: -pool[m][0]))}
    sr = {m: i+1 for i, m in enumerate(sorted(pool, key=lambda m: -pool[m][1]))}
    RANKC[key] = (ur, sr, pool)
    return RANKC[key]

# ---- injuries: player -> sorted list of (utc, status) ----
inj = collections.defaultdict(list)
for r in load("injuries_log.csv"):
    t = ts(r.get("captured_utc"))
    if not t: continue
    inj[_pl(r.get("player"))].append((t, (r.get("status") or "").strip()))
for v in inj.values(): v.sort()
def status_at(pl, when):
    """last flag posted BEFORE tip. no look-ahead."""
    best = None
    for t, s in inj.get(pl, ()):
        if t <= when: best = s
        else: break
    return best

# ---- team game tips, in order ----
tips_team = collections.defaultdict(set)
for (pl, tp), row in pgrow.items(): tips_team[row["tm"]].add(tp)
tips_team = {t: sorted(v) for t, v in tips_team.items()}

# ---- teammate-absence flag for a team-game: who played the PREVIOUS game with >=25 med min
#      but is NOT in tonight's box, or is flagged Out before tip ----
def absences(tm, gt):
    ti = tips_team[tm]
    i = ti.index(gt)
    if i == 0: return []
    here = roster.get((tm, gt), set())
    out = []
    # candidate pool = anyone who has played >=3 current-team games before tonight
    cands = set()
    for j in range(max(0, i-6), i):
        cands |= roster.get((tm, ti[j]), set())
    for m in cands:
        pv = prior_ct(m, tm, gt)
        if len(pv) < 3: continue
        medmin = statistics.median(x["min"] for x in pv[-10:])
        if medmin < 25: continue
        st = (status_at(m, gt) or "").lower()
        if m not in here or st in ("out", "doubtful"):
            out.append((m, medmin, st))
    return out

ROWS = []
skip = collections.Counter()
for (pl, mk, gt), sd in side.items():
    if "Over" not in sd or "Under" not in sd: skip["one-sided"] += 1; continue
    if sd["Over"][1] != sd["Under"][1]: skip["line-mismatch"] += 1; continue
    now = pgrow.get((pl, gt))
    if not now: skip["dnp"] += 1; continue
    line = sd["Over"][1]
    if now[mk] == line: skip["push"] += 1; continue
    tm = now["tm"]
    pv = prior_ct(pl, tm, gt)
    if len(pv) < 5: skip["<5 prior current-team"] += 1; continue
    ur, sr, pool = ranks_for(tm, gt)
    if pl not in ur: skip["not in rank pool"] += 1; continue
    last10 = pv[-10:]
    medmin = statistics.median(x["min"] for x in last10)
    medstat = statistics.median(x[mk] for x in last10)
    ti = tips_team[tm]; i = ti.index(gt)
    # minutes in the PREVIOUS game vs the median of the 10 games before THAT (known pre-tip)
    prev = pv[-1]
    pv2 = [x for x in pv if x["tip"] < prev["tip"]]
    prev_jump = None
    if len(pv2) >= 5:
        prev_jump = prev["min"] - statistics.median(x["min"] for x in pv2[-10:])
    ab = absences(tm, gt)
    ROWS.append(dict(pl=pl, mk=mk, tip=gt.isoformat(), date=now["date"], tm=tm, line=line,
                     over_od=sd["Over"][2], under_od=sd["Under"][2],
                     over_won=bool(now[mk] > line),
                     actual=now[mk], min=now["min"],
                     urank=ur[pl], srank=sr[pl], pool=len(ur),
                     npg=len(pv), medmin=medmin, medstat=medstat,
                     prev_min=prev["min"], prev_jump=prev_jump,
                     prev_tip=prev["tip"].isoformat(),
                     game_idx=i, newly=(pl in NEWLY),
                     n_abs=len(ab), abs_names=[a[0] for a in ab],
                     abs_minmed=(max(a[1] for a in ab) if ab else 0.0)))
print("skips:", dict(skip))
print("rows:", len(ROWS), " players:", len(set(r["pl"] for r in ROWS)),
      " player-games:", len(set((r["pl"], r["tip"]) for r in ROWS)),
      " games:", len(set((r["tm"], r["tip"]) for r in ROWS)))
print("newly-resolved rows:", sum(1 for r in ROWS if r["newly"]))
json.dump(ROWS, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "role_rows.json"), "w"))
