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
    ALL.append(dict(pl=pl, mk=mk, date=now["date"], odds=price, won=now[mk] > line,
                    star=(line - pv < 0.5), mates_out=sum(1 for m in top3 if m not in here)))

def roi(rows): return sum((r["odds"]-1) if r["won"] else -1.0 for r in rows)/len(rows) if rows else 0.0
def one_per_player(rows):
    byday = collections.defaultdict(list)
    for r in rows: byday[r["date"]].append(r)
    out = []
    for dd, v in byday.items():
        best = {}
        for r in sorted(v, key=lambda x: -x["odds"]): best.setdefault(r["pl"], r)
        out += list(best.values())
    return out

print("="*100)
print("  A DISCREPANCY I NEED TO OWN: which dedup does the headline +23.5% use?")
print("="*100)
for lbl, rows in (("one per PLAYER-MARKET-game", ALL),
                  ("one per PLAYER per day  (the live 'ONE position' rule)", one_per_player(ALL))):
    S_ = [r for r in rows if r["star"]]; R_ = [r for r in rows if not r["star"]]
    print(f"  {lbl}")
    print(f"    starred  n={len(S_):<4} {100*sum(1 for r in S_ if r['won'])/len(S_):5.1f}%  ROI {100*roi(S_):+6.1f}%")
    print(f"    raised   n={len(R_):<4} {100*sum(1 for r in R_ if r['won'])/len(R_):5.1f}%  ROI {100*roi(R_):+6.1f}%")
    print(f"    star gap {100*(roi(S_)-roi(R_)):+.1f}pp")
    ns = len(S_)
    sims = []
    for _ in range(20000):
        idx = list(range(len(rows))); random.shuffle(idx)
        a = [rows[i] for i in idx[:ns]]; b = [rows[i] for i in idx[ns:]]
        sims.append(roi(a) - roi(b))
    gap = roi(S_) - roi(R_)
    beat = sum(1 for x in sims if x >= gap)
    sims.sort()
    print(f"    random-split control: p95 gap {100*sims[19000]:+.1f}pp   ->  p = {beat/20000:.4f}")
    print("")
print("  The card WARNS when a player appears twice but the tracker logs BOTH rows, so the")
print("  headline has been quoting the player-market version. Under the rule we actually bet")
print("  - one position per player - the number is the lower one.")
