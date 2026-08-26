# build_B.py - event table for the BACKUP-ELEVATED-BY-INJURY hypothesis.
# Two event detectors, both computable BEFORE the bet game:
#   JUMP  : in a PAST game G her minutes beat her trailing median by >= THRESH
#   INJOUT: a team-mate with >=25 median minutes carries an Out/Doubtful flag posted
#           BEFORE tonight's tip (injuries_log), or was absent from a PAST game's box.
# The bet game is always strictly after the game that created the event.
import os, sys, json, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rolelib as L
g = L.boot()
pgrow, hist, roster, gmeta = g["pgrow"], g["hist"], g["roster"], g["gmeta"]
side, teamof, load, ts, _pl = g["side"], g["teamof"], g["load"], g["ts"], g["_pl"]

HD = os.path.dirname(os.path.abspath(__file__))
ROWS = json.load(open(os.path.join(HD, "role_rows.json")))
import datetime
def T(s): return datetime.datetime.fromisoformat(s)

# team game calendar
tips_team = collections.defaultdict(set)
for (pl, tp), row in pgrow.items(): tips_team[row["tm"]].add(tp)
tips_team = {t: sorted(v) for t, v in tips_team.items()}

def prior_ct(pl, tm, gt): return [x for x in hist.get(pl, []) if x["tip"] < gt and x["tm"] == tm]

# ---------- 1. THE JUMP DISTRIBUTION: threshold comes from the data, not from a hunch ----------
J = []
for (pl, gt), row in pgrow.items():
    pv = prior_ct(pl, row["tm"], gt)
    if len(pv) < 5: continue
    J.append((pl, gt, row["tm"], row["min"] - statistics.median(x["min"] for x in pv[-10:]),
              statistics.median(x["min"] for x in pv[-10:]), row["min"]))
d = sorted(x[3] for x in J)
q = lambda p: d[int(p*len(d))]
print("MINUTES-JUMP DISTRIBUTION over %d player-games (min - trailing median of last 10):" % len(d))
print("   p50 %+.1f  p75 %+.1f  p90 %+.1f  p95 %+.1f  p97.5 %+.1f  p99 %+.1f  max %+.1f" %
      (q(.50), q(.75), q(.90), q(.95), q(.975), q(.99), d[-1]))
THRESH = round(q(.90))
print("   THRESHOLD = p90 = +%d minutes (declared from the distribution, not chosen)" % THRESH)
JUMP = set((p, gt) for p, gt, tm, dl, md, mn in J if dl >= THRESH)
JUMPBIG = set((p, gt) for p, gt, tm, dl, md, mn in J if dl >= THRESH and md <= 22 and mn >= 26)
print("   jump events: %d   of which genuine-backup (base med<=22 min AND jumped to >=26): %d"
      % (len(JUMP), len(JUMPBIG)))

# ---------- 2. injuries: pre-tip status ----------
inj = collections.defaultdict(list)
for r in load("injuries_log.csv"):
    t = ts(r.get("captured_utc"))
    if t: inj[_pl(r.get("player"))].append((t, (r.get("status") or "").strip().lower()))
for v in inj.values(): v.sort()
def status_at(pl, when):
    best = None
    for t, s in inj.get(pl, ()):
        if t <= when: best = s
        else: break
    return best

def heavy_mates(tm, gt):
    """team-mates with >=25 median minutes going into tonight, from PRIOR games only"""
    out = {}
    ti = tips_team[tm]; i = ti.index(gt)
    cands = set()
    for j in range(max(0, i-6), i): cands |= roster.get((tm, ti[j]), set())
    for m in cands:
        pv = prior_ct(m, tm, gt)
        if len(pv) < 3: continue
        md = statistics.median(x["min"] for x in pv[-10:])
        if md >= 25: out[m] = md
    return out

# ---------- 3. attach event features to every gradable quote ----------
out = []
for r in ROWS:
    gt = T(r["tip"]); tm = r["tm"]; pl = r["pl"]
    ti = tips_team[tm]; i = ti.index(gt)
    # how many of HER team's games ago was her most recent jump? (strictly before tonight)
    k_jump = None; k_jumpbig = None
    for back in (1, 2, 3, 4):
        if i-back < 0: break
        gprev = ti[i-back]
        if k_jump is None and (pl, gprev) in JUMP: k_jump = back
        if k_jumpbig is None and (pl, gprev) in JUMPBIG: k_jumpbig = back
    hm = heavy_mates(tm, gt)
    # ARM 2a: heavy mate flagged Out/Doubtful BEFORE tip tonight  (clean, pre-tip)
    out_now = [m for m, md in hm.items() if (status_at(m, gt) or "") in ("out", "doubtful")]
    # ARM 2b: heavy mate missing from a PAST game's box -> how many games ago did that start?
    k_gone = None
    for back in (1, 2, 3, 4):
        if i-back < 0: break
        gp = ti[i-back]
        gone = [m for m in hm if m not in roster.get((tm, gp), set())]
        if gone: k_gone = back; break
    # her own baseline going in
    out.append(dict(r, k_jump=k_jump, k_jumpbig=k_jumpbig,
                    n_out_now=len(out_now), k_gone=k_gone,
                    backup=(r["medmin"] <= 22)))
json.dump(out, open(os.path.join(HD, "B_rows.json"), "w"))
c = collections.Counter()
for r in out:
    c["k_jump=%s" % r["k_jump"]] += 1
    c["k_gone=%s" % r["k_gone"]] += 1
    c["out_now>0"] += 1 if r["n_out_now"] else 0
print("\nquote counts by event index:", dict(sorted(c.items())))
print("rows:", len(out))
