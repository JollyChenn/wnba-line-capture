# Shared builder for the cross-market movement study. Imported via exec() by the analysis scripts.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

UTC = datetime.timezone.utc
def aware(t):
    if t is None: return None
    return t.replace(tzinfo=UTC) if t.tzinfo is None else t

# ---------- game identity: (tip, frozenset(teams)) resolved from every source -------------
bypair = collections.defaultdict(list)
for gid,(dt,tp,hm,aw) in gmeta.items():
    bypair[tuple(sorted((hm,aw)))].append((aware(tp),gid))
def resolve(ab, start):
    st = aware(ts(start))
    if st is None: return None
    best=None
    for tp,gid in bypair.get(ab,[]):
        d=abs((tp-st).total_seconds())
        if best is None or d<best[0]: best=(d,gid,tp)
    if best and best[0] <= 30*3600: return best[1]
    return None

# ---------- Pinnacle game-market time series, per game_id ----------
PT = collections.defaultdict(list)   # total   [(cap, points, over_prob)]
PS = collections.defaultdict(list)   # spread  [(cap, home_points, home_prob)]  points signed on HOME
PM = collections.defaultdict(list)   # moneyline [(cap, home_prob)]
_cache={}
for r in load("gamelines.csv"):
    tm=(r.get("teams") or "").split("|")
    if len(tm)!=2: continue
    names=[t.strip() for t in tm]
    ab=tuple(sorted(FULL.get(t,"") for t in names))
    if "" in ab: continue
    ck=(ab, r.get("start"))
    if ck not in _cache: _cache[ck]=resolve(ab, r.get("start"))
    gid=_cache[ck]
    if not gid: continue
    cap=aware(ts(r.get("captured_utc"))); pts=f(r.get("points"))
    if not cap: continue
    pr=(r.get("prices") or "").split(",")
    p0 = am(pr[0]) if len(pr)>0 and pr[0] else None
    ty=r.get("type")
    # gamelines 'teams' is "A|B"; prices are in that order. home team from gmeta.
    hm = gmeta[gid][2]
    first_is_home = (FULL.get(names[0],"")==hm)
    if ty=="total" and pts is not None:
        PT[gid].append((cap, pts, p0))              # p0 = OVER price (first listed)
    elif ty=="spread" and pts is not None:
        # points as listed belongs to first-listed team
        hp = pts if first_is_home else -pts
        PS[gid].append((cap, hp, p0 if first_is_home else (am(pr[1]) if len(pr)>1 and pr[1] else None)))
    elif ty=="moneyline" and p0 is not None:
        hp = p0 if first_is_home else (am(pr[1]) if len(pr)>1 and pr[1] else None)
        if hp is not None: PM[gid].append((cap, hp))
for d in (PT,PS,PM):
    for v in d.values(): v.sort(key=lambda x:x[0])

# ---------- 1xbet game markets ----------
XT = collections.defaultdict(list); XS = collections.defaultdict(list)
_c2={}
for r in load("xbet_gamelines.csv"):
    tm=(r.get("teams") or "").split("|")
    if len(tm)!=2: continue
    names=[t.strip() for t in tm]
    ab=tuple(sorted(FULL.get(t,"") for t in names))
    if "" in ab: continue
    ck=(ab,r.get("start"))
    if ck not in _c2: _c2[ck]=resolve(ab,r.get("start"))
    gid=_c2[ck]
    if not gid: continue
    cap=aware(ts(r.get("captured_utc"))); pts=f(r.get("points"))
    if not cap: continue
    if r.get("type")=="total" and pts is not None: XT[gid].append((cap,pts,f(r.get("p1"))))
    elif r.get("type")=="spread" and pts is not None:
        hm=gmeta[gid][2]; first_is_home=(FULL.get(names[0],"")==hm)
        XS[gid].append((cap, pts if first_is_home else -pts, None))
for d in (XT,XS):
    for v in d.values(): v.sort(key=lambda x:x[0])

# ---------- player prop time series, per (player, market, game_id) ----------
tip_to_gid = {}
for gid,(dt,tp,hm,aw) in gmeta.items(): tip_to_gid[aware(tp)] = gid
PROP = collections.defaultdict(lambda: {"Over":[], "Under":[]})
for r in load("xbet_board.csv"):
    t=aware(ts(r.get("captured_utc"))); ln=f(r.get("line")); od=f(r.get("odds"))
    if not t or ln is None or od is None: continue
    pl=(r.get("player") or "").lower(); mk=r.get("market"); sd=r.get("side")
    if mk not in ALL_MK or sd not in ("Over","Under"): continue
    tm=teamof.get(pl)
    if not tm: continue
    gt=game_for(tm,t)
    if not gt: continue
    gt=aware(gt); gid=tip_to_gid.get(gt)
    if not gid: continue
    PROP[(pl,mk,gid)][sd].append((t,ln,od))
for v in PROP.values():
    for s in v: v[s].sort(key=lambda x:x[0])

def at_or_before(series, when, idx=1):
    """last value in series at or before `when`; series items are tuples (cap, ...)."""
    best=None
    for it in series:
        if it[0] <= when: best=it
        else: break
    return best

def two_sided_at(pl, mk, gid, when):
    """last quote instant at-or-before `when` where BOTH sides are posted at the SAME line.
       returns (cap, line, over_odds, under_odds) or None."""
    s = PROP.get((pl,mk,gid))
    if not s: return None
    ov=[x for x in s["Over"] if x[0]<=when]; un=[x for x in s["Under"] if x[0]<=when]
    if not ov or not un: return None
    # walk Over backwards, find the nearest Under with same line within 90 min
    for t,ln,od in reversed(ov):
        cand=[u for u in un if u[1]==ln and abs((u[0]-t).total_seconds())<=90*60]
        if cand:
            u=min(cand,key=lambda u:abs((u[0]-t).total_seconds()))
            return (t, ln, od, u[2])
    return None
