# star_gauntlet.py - two things: the teammate split on our own 99 bets, and then the honest
# question - why does the star clear tests that killed twelve other ideas?
# ---------------------------------------------------------------------------------------------
# The fair way to answer that is to run the star through the SAME gauntlet everything else
# failed, on the same data, with the same controls. No special pleading.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260904)
D = os.path.dirname(os.path.abspath(__file__))

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

MKTS = ("pra", "pr", "pts"); SIGS = ("flip", "hotover", "overshoot")
gmeta = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: gmeta[g.get("game_id")] = (g.get("date", ""), t)
pgrow = {}; roster = collections.defaultdict(set); teamof = {}
for r in load("data/box_2026.csv"):
    gid = r.get("game_id")
    if gid not in gmeta: continue
    dt, tp = gmeta[gid]
    pl, tm = (r.get("player") or "").lower(), r.get("team")
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    use = (f(r.get("fga")) or 0) + 0.44*(f(r.get("fta")) or 0) + (f(r.get("to")) or 0)
    pgrow[(pl, tp)] = dict(tm=tm, tip=tp, date=dt, use=use, pts=p_, pra=p_+rb+a, pr=p_+rb)
    roster[(tm, tp)].add(pl); teamof[pl] = tm
hist = collections.defaultdict(list)
for (pl, tp), row in pgrow.items(): hist[pl].append(row)
for v in hist.values(): v.sort(key=lambda x: x["tip"])

tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t: tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()
def game_for(tm, when):
    for t in tips_of.get(tm, []):
        if when <= t and (t-when).total_seconds() <= 60*3600: return t
    return None
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = teamof.get(pl)
    if not tm: continue
    for t, o in sorted(v):
        g2 = game_for(tm, t)
        if g2: bygame[(pl, mk, g2)].append((t, ln, o))
for v in bygame.values(): v.sort()

# ALL model candidates (both sides of the star) so the star itself can be tested
seen, ALL = set(), []
for b in sorted(load("bets_log.csv"), key=lambda r: r.get("captured_utc") or ""):
    if b.get("side") != "Over" or b.get("src") not in SIGS: continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    t0, tm = ts(b.get("captured_utc")), teamof.get(pl)
    if not (t0 and tm): continue
    gt = game_for(tm, t0)
    if not gt or (pl, mk, gt) in seen: continue
    seq = bygame.get((pl, mk, gt), []); now = pgrow.get((pl, gt))
    if not seq or not now: continue
    line, price = seq[-1][1], seq[-1][2]
    if now[mk] == line: continue
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < gt)
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    if pv is None: continue
    seen.add((pl, mk, gt))
    p5 = [x for x in hist.get(pl, []) if x["tip"] < gt][-5:]
    mates = collections.Counter()
    for r5 in p5:
        for m in roster.get((r5["tm"], r5["tip"]), ()):
            if m != pl: mates[m] += pgrow[(m, r5["tip"])]["use"]
    top3 = [m for m, _ in mates.most_common(3)]
    here = roster.get((now["tm"], gt), set())
    ALL.append(dict(pl=pl, mk=mk, src=b.get("src"), date=now["date"], odds=price, won=now[mk] > line,
                    star=(line - pv < 0.5), mates_out=sum(1 for m in top3 if m not in here)))

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
print("="*100)
print("  DOES THE STAR REPLICATE INSIDE EACH SIGNAL SEPARATELY?")
print("  This is the evidence I have leaned on hardest. A lucky split of the pooled set would")
print("  NOT improve every signal independently, so it is the real test.")
print("="*100)
print(f"  {'signal':<12}{'RAW':>22}{'STARRED':>22}{'RAISED':>22}")
for s_ in ("flip", "overshoot", "hotover"):
    g = [r for r in ALL if r["src"] == s_]
    st = [r for r in g if r["star"]]; rz = [r for r in g if not r["star"]]
    def cell(v):
        if len(v) < 8: return f"n={len(v)} too few".rjust(22)
        return f"n={len(v)} {100*sum(1 for r in v if r['won'])/len(v):.0f}% {100*roi(v):+.1f}%".rjust(22)
    print(f"  {s_:<12}{cell(g)}{cell(st)}{cell(rz)}")
print("")
print("  and pooled:")
st = [r for r in ALL if r["star"]]; rz = [r for r in ALL if not r["star"]]
print(f"    starred n={len(st)} {100*roi(st):+.1f}%   raised n={len(rz)} {100*roi(rz):+.1f}%")
print("")
print("="*100)
print("  HOW OFTEN DOES A RANDOM SPLIT IMPROVE *EVERY* SIGNAL AT ONCE?")
print("="*100)
sigs = [s_ for s_ in ("flip","overshoot","hotover") if len([r for r in ALL if r["src"]==s_]) >= 20]
real_ok = all(roi([r for r in ALL if r["src"]==s_ and r["star"]]) >
              roi([r for r in ALL if r["src"]==s_ and not r["star"]]) for s_ in sigs)
print(f"  signals with n>=20: {sigs}")
print(f"  does the REAL star improve all of them? {real_ok}")
ns = len(st); T = 20000; hits = 0
for _ in range(T):
    idx = list(range(len(ALL))); random.shuffle(idx)
    fake = set(idx[:ns])
    ok = True
    for s_ in sigs:
        a = [ALL[i] for i in range(len(ALL)) if ALL[i]["src"]==s_ and i in fake]
        b = [ALL[i] for i in range(len(ALL)) if ALL[i]["src"]==s_ and i not in fake]
        if len(a) < 5 or len(b) < 5: ok = False; break
        if roi(a) <= roi(b): ok = False; break
    if ok: hits += 1
print(f"  a random split improves ALL of them in {hits}/{T} = {100*hits/T:.1f}% of trials")
print("")
print("  That is the number that matters: not whether one pooled gap is impressive, but whether")
print("  the same cut helps every signal independently - which chance rarely arranges.")
