import csv, os, sys, math, random, statistics, datetime, collections, re, json
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

# ---------- per-quarter production from play-by-play ----------
MKre = re.compile(r"^(.+?) makes (.+)$")
qp = collections.defaultdict(lambda: [0.0]*4)
for r in load("elo_model/plays_full.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    try: per = int(r.get("period") or 0)
    except Exception: continue
    if per < 1: continue
    m = MKre.match(r.get("text") or "")
    if not m: continue
    nm = m.group(1).strip().lower(); tail = m.group(2).lower()
    qp[(gid, nm)][min(per,4)-1] += (1 if "free throw" in tail else (3 if "three point" in tail else 2))

# gid -> tip/date/teams
gid_tip = {g:v[1] for g,v in gmeta.items()}
# player-game quarter rows, keyed by player, sorted by tip, with team from box
boxteam = {}
for r in load("data/box_2026.csv"):
    boxteam[(r.get("game_id"), (r.get("player") or "").lower())] = r.get("team")
QROWS = collections.defaultdict(list)   # player -> [(tip, team, [q1..q4])]
for (gid, nm), v in qp.items():
    tp = gid_tip.get(gid); tm = boxteam.get((gid, nm))
    if tp is None or tm is None: continue
    QROWS[nm].append((tp, tm, v))
for v in QROWS.values(): v.sort(key=lambda x: x[0])

# ---------- halves file (points only, 0508-0622) : team H1/H2 split ----------
HAL = collections.defaultdict(list)  # team -> [(tip, h1, h2)]
tm_acc = collections.defaultdict(lambda: [0.0,0.0])
for r in load("data/halves_2026.csv"):
    gid = r.get("game_id"); pl = (r.get("player") or "").lower()
    tm = boxteam.get((gid, pl)); tp = gid_tip.get(gid)
    if not tm or tp is None: continue
    tm_acc[(tm, tp)][0] += f(r.get("h1_pts")) or 0
    tm_acc[(tm, tp)][1] += f(r.get("h2_pts")) or 0
# also team halves from plays (wider window): team quarter totals
tq = collections.defaultdict(lambda: [0.0]*4)
for (gid, nm), v in qp.items():
    tm = boxteam.get((gid, nm)); tp = gid_tip.get(gid)
    if not tm or tp is None: continue
    for i in range(4): tq[(tm, tp)][i] += v[i]
TEAMG = collections.defaultdict(list)
for (tm, tp), v in tq.items(): TEAMG[tm].append((tp, v))
for v in TEAMG.values(): v.sort(key=lambda x: x[0])

MINPRIOR = 5

def prof(pl, tm, gt):
    """timing profile from prior games on CURRENT team only (Law 4)."""
    rows = [r for r in QROWS.get(pl, []) if r[0] < gt and r[1] == tm]
    if len(rows) < MINPRIOR: return None
    tot = [sum(r[2]) for r in rows]
    S = sum(tot)
    if S < 25: return None
    q = [sum(r[2][i] for r in rows) for i in range(4)]
    h1share = (q[0]+q[1])/S
    q4share = q[3]/S
    # per-game concentration (HHI over quarter shares), games with >=4 pts
    hh = []
    for r in rows:
        t = sum(r[2])
        if t >= 4: hh.append(sum((x/t)**2 for x in r[2]))
    if len(hh) < 4: return None
    qconc = statistics.mean(hh)
    # appearance-in-Q4 proxy: fraction of prior games she scored in Q4
    q4app = sum(1 for r in rows if r[2][3] > 0)/len(rows)
    sd_pts = statistics.pstdev(tot) if len(tot) > 1 else 0.0
    mn_pts = statistics.mean(tot)
    cv = sd_pts/mn_pts if mn_pts > 0 else 0.0
    return dict(h1share=h1share, q4share=q4share, qconc=qconc, q4app=q4app,
                cv=cv, sd_pts=sd_pts, ng=len(rows))

def teamprof(tm, gt):
    rows = [r for r in TEAMG.get(tm, []) if r[0] < gt]
    if len(rows) < MINPRIOR: return None
    S = sum(sum(r[1]) for r in rows)
    if S <= 0: return None
    q = [sum(r[1][i] for r in rows) for i in range(4)]
    return (q[0]+q[1])/S

# ---------- attach to board ----------
R = []
for r in B:
    p = prof(r["pl"], r["tm"], r["gt"])
    if not p: continue
    tp = teamprof(r["tm"], r["gt"])
    q = dict(r); q.update(p); q["team_h1"] = tp
    now = pgrow.get((r["pl"], r["gt"]))
    q["resid"] = now[r["mk"]] - r["line"]
    R.append(q)
print(f"board quotes with timing profile: {len(R)} / {len(B)}")
print("players:", len(set(x['pl'] for x in R)), " games:", len(set(x['gt'] for x in R)))
print("markets:", collections.Counter(x['mk'] for x in R))
print("team_h1 present:", sum(1 for x in R if x['team_h1'] is not None))
print("date range:", min(x['date'] for x in R), max(x['date'] for x in R))
for k in ("h1share","q4share","qconc","q4app","cv","ng"):
    v = sorted(x[k] for x in R)
    print(f"  {k:<9} p10={v[len(v)//10]:.3f} med={v[len(v)//2]:.3f} p90={v[9*len(v)//10]:.3f}")
json.dump([{k:(v.isoformat() if isinstance(v,datetime.datetime) else v) for k,v in x.items()} for x in R],
          open(os.path.join(D,"tim_rows.json"),"w"))
print("wrote tim_rows.json")
