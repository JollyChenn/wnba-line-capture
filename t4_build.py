# TRACK 4 base table builder. Read-only. Writes outputs/t4_base.json
import csv, os, sys, math, random, statistics, datetime, collections, json, unicodedata, re
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

# ---------------- time-aware team map ----------------
pteam = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): pteam[pl].append((tp, row["tm"]))
for v in pteam.values(): v.sort()
def team_at(pl, when):
    v = pteam.get(pl, [])
    prior = [t for t in v if t[0] < when]
    if prior: return prior[-1][1]
    return v[0][1] if v else None

def game_for2(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None

# ---------------- board quotes ----------------
QQ = collections.defaultdict(list)
nb = 0
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None): continue
    if b.get("market") not in ALL_MK: continue
    sd = b.get("side")
    if sd not in ("Over", "Under"): continue
    pl = (b.get("player") or "").lower()
    tm = team_at(pl, t)
    if not tm: continue
    gt = game_for2(tm, t)
    if not gt: continue
    QQ[(pl, b.get("market"), gt, sd)].append((t, ln, o))
    nb += 1
for v in QQ.values(): v.sort()
print("board quotes assigned to games: %d" % nb)

def snap(pl, mk, gt, hrs):
    cut = gt if hrs is None else gt - datetime.timedelta(hours=hrs)
    ov = [x for x in QQ.get((pl, mk, gt, "Over"), []) if x[0] <= cut]
    if not ov: return None
    t, ln, oo = ov[-1]
    un = [x for x in QQ.get((pl, mk, gt, "Under"), []) if x[0] <= cut and abs(x[1]-ln) < 0.01]
    if not un: return None
    return dict(t=t, line=ln, over=oo, under=un[-1][2])

def snap_open(pl, mk, gt):
    ov = QQ.get((pl, mk, gt, "Over"), [])
    if not ov: return None
    t, ln, oo = ov[0]
    un = [x for x in QQ.get((pl, mk, gt, "Under"), []) if abs(x[1]-ln) < 0.01]
    if not un: return None
    return dict(t=t, line=ln, over=oo, under=un[0][2])

# ---------------- previous-game line ----------------
lastln = collections.defaultdict(dict)
for (pl, mk, gt, sd), v in QQ.items():
    if sd != "Over": continue
    lastln[(pl, mk)][gt] = v[-1][1]
PREV = {}
for k, dd in lastln.items():
    gs = sorted(dd)
    for i in range(1, len(gs)): PREV[(k[0], k[1], gs[i])] = dd[gs[i-1]]

# ---------------- signals from bets_log ----------------
SIG = collections.defaultdict(set)
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    t = ts(b.get("captured_utc"))
    if not t: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in ALL_MK: continue
    tm = team_at(pl, t)
    if not tm: continue
    gt = game_for2(tm, t)
    if not gt: continue
    SIG[(pl, mk, gt)].add(b.get("src") or "?")

# ---------------- Pinnacle sharp lines ----------------
def pkey(name):
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii","ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip() or str(name or "").lower()
sharp_raw = collections.defaultdict(list)
for r in load("pinn_board.csv"):
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    if t and ln is not None: sharp_raw[(pkey(r.get("player")), r.get("market"))].append((t, ln))
for r in load("bets_log.csv"):
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn"))
    if t and ln is not None: sharp_raw[(pkey(r.get("player")), r.get("market"))].append((t, ln))
for v in sharp_raw.values(): v.sort()
def sharp_at(pl, mk, gt, max_age_h=10.0, asof_h=6.0):
    cut = gt - datetime.timedelta(hours=asof_h)
    v = sharp_raw.get((pkey(pl), mk), [])
    fresh = [x for x in v if x[0] <= cut and (cut - x[0]).total_seconds() <= max_age_h*3600]
    return fresh[-1][1] if fresh else None

# ---------------- game totals ----------------
GT_ = collections.defaultdict(list)
for r in load("gamelines.csv"):
    if r.get("type") != "total": continue
    st = (r.get("start") or "")[:10].replace("-", "")
    tm = (r.get("teams") or "").split("|")
    if len(tm) != 2: continue
    ab = tuple(sorted(FULL.get(t.strip(), "") for t in tm))
    if "" in ab: continue
    cap, pts = ts(r.get("captured_utc")), f(r.get("points"))
    if cap and pts is not None: GT_[(st, ab)].append((cap, pts))
for v in GT_.values(): v.sort()

OPP = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    OPP[(hm, t2)] = (d2, aw); OPP[(aw, t2)] = (d2, hm)
GRES = {}
for gid, (d2, t2, hm, aw) in gmeta.items():
    GRES[(d2, hm)] = t2
# realised team scores for mechanism check on totals
tscore = collections.defaultdict(float)
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp, hm, aw = gmeta[gid]
    tscore[(tp, r.get("team"))] += (f(r.get("pts")) or 0)

# ---------------- assemble ----------------
ROWS = []
for (pl, mk, gt, sd) in list(QQ):
    if sd != "Over": continue
    now = pgrow.get((pl, gt))
    if not now or now["min"] < 8: continue
    s_late = snap(pl, mk, gt, 1.0)
    s_open = snap_open(pl, mk, gt)
    s_6h   = snap(pl, mk, gt, 6.0)
    if not s_late or not s_open: continue
    prior = [x for x in hist.get(pl, []) if x["tip"] < gt]
    if len(prior) < 6: continue
    tm = now["tm"]
    p10 = prior[-10:]
    ct = [x for x in prior if x["tm"] == tm][-10:]
    relvol = (statistics.pstdev([x[mk] for x in ct]) / max(s_late["line"], 1.0)) if len(ct) >= 6 else None
    sdv    = statistics.pstdev([x[mk] for x in ct]) if len(ct) >= 6 else None
    mean_ct = (statistics.mean([x[mk] for x in ct]) if len(ct) >= 6 else None)
    med10 = statistics.median(x[mk] for x in p10)
    prev = PREV.get((pl, mk, gt))
    od = OPP.get((tm, gt))
    tot = None
    if od:
        key = (od[0], tuple(sorted((tm, od[1]))))
        v = [x for x in GT_.get(key, []) if x[0] <= gt]
        if v: tot = v[-1][1]
    realtot = None
    if od:
        a = tscore.get((gt, tm)); b2 = tscore.get((gt, od[1]))
        if a and b2: realtot = a + b2
    sl = sharp_at(pl, mk, gt, 10.0, 6.0)
    sl12 = sharp_at(pl, mk, gt, 14.0, 12.0)
    srcs = sorted(SIG.get((pl, mk, gt), ()))
    ROWS.append(dict(
        pl=pl, mk=mk, tm=tm, date=now["date"], gt=gt.isoformat(),
        opp=(od[1] if od else None),
        actual=now[mk], minutes=now["min"],
        line=s_late["line"], over=s_late["over"], under=s_late["under"], entry_t=s_late["t"].isoformat(),
        oline=s_open["line"], oover=s_open["over"], ounder=s_open["under"], open_t=s_open["t"].isoformat(),
        l6=(s_6h["line"] if s_6h else None), o6=(s_6h["over"] if s_6h else None),
        u6=(s_6h["under"] if s_6h else None),
        prev=prev, med10=med10, relvol=relvol, sd=sdv, mean_ct=mean_ct,
        tot=tot, realtot=realtot, sharp=sl, sharp12=sl12,
        srcs=srcs, nprior=len(prior)))
print("ROWS = %d  games = %d  players = %d" % (len(ROWS), len(set(r['gt'] for r in ROWS)), len(set(r['pl'] for r in ROWS))))
for k in ("prev", "sharp", "tot", "relvol", "realtot"):
    print("  with %-8s %d" % (k, sum(1 for r in ROWS if r[k] is not None)))
print("  with any src:", sum(1 for r in ROWS if r["srcs"]))
print("  src counts:", collections.Counter(s for r in ROWS for s in r["srcs"]).most_common())
print("  date range:", min(r["date"] for r in ROWS), max(r["date"] for r in ROWS))
json.dump(ROWS, open(os.path.join(D, "outputs", "t4_base.json"), "w"), default=str)
print("written outputs/t4_base.json")
