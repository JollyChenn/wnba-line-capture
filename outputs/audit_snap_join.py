import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
R = os.path.dirname(D)

def load(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

def ts(s):
    s = (s or "").strip().replace("Z","")
    for fmt in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.datetime.strptime(s, fmt)
        except Exception: pass
    return None

FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
        "Golden State Valkyries":"GS","Indiana Fever":"IND","Las Vegas Aces":"LV",
        "Los Angeles Sparks":"LA","Minnesota Lynx":"MIN","New York Liberty":"NY",
        "Phoenix Mercury":"PHX","Portland Fire":"POR","Toronto Tempo":"TOR","Seattle Storm":"SEA","Washington Mystics":"WSH"}

games = load(os.path.join(R,"data","games_2026.csv"))
gmeta = {}
for g in games:
    t = ts(g.get("tip",""))
    if t: gmeta[g["game_id"]] = (t, g["home"], g["away"])

snaps = load(os.path.join(R,"live_snapshots.csv"))
by_gid = collections.defaultdict(list)
for s in snaps:
    t = ts(s["ts"])
    if t: by_gid[s["game_id"]].append((t,s))
for k in by_gid: by_gid[k].sort(key=lambda x:x[0])

print("=== FILE BASICS ===")
print("snapshot rows=%d  distinct game_ids=%d" % (len(snaps), len(by_gid)))

lines = load(os.path.join(R,"live_lines.csv"))
print("live_lines rows=%d" % len(lines))

pair2gids = collections.defaultdict(list)
for gid,(t,h,a) in gmeta.items():
    pair2gids[frozenset([h,a])].append((t,gid))

WIN_H = 3.0
inplay = []
unmapped = 0
for r in lines:
    t = ts(r["ts"])
    if not t: continue
    parts = (r.get("teams") or "").split("|")
    abbr = frozenset(FULL.get(p.strip(),"?") for p in parts)
    cands = pair2gids.get(abbr)
    if not cands: unmapped += 1; continue
    best = None
    for tp,gid in cands:
        d = (t-tp).total_seconds()
        if 0 <= d <= WIN_H*3600:
            if best is None or d < best[0]: best = (d,gid)
    if best: inplay.append((t,best[1]))

gids_inplay = collections.Counter(g for _,g in inplay)
print("")
print("=== IN-PLAY, DEFINED BY TIP TIME (independent of snapshots) ===")
print("in-play odds rows=%d  distinct games=%d  unmapped team-pairs=%d" % (len(inplay), len(gids_inplay), unmapped))

def nearest(gid, t):
    arr = by_gid.get(gid)
    if not arr: return None
    return min(abs((t-x[0]).total_seconds()) for x in arr)

deltas = []
per_game_match = collections.Counter(); per_game_tot = collections.Counter()
nogid = 0
for t,gid in inplay:
    per_game_tot[gid]+=1
    d = nearest(gid,t)
    if d is None: nogid+=1; continue
    deltas.append(d)
    if d <= 90: per_game_match[gid]+=1
matched = sum(1 for d in deltas if d<=90)
print("odds rows whose game has NO snapshot at all: %d" % nogid)
print("matched within 90s: %d/%d = %.1f%%" % (matched, len(inplay), matched/len(inplay)*100))
print("median |dt| = %.0fs   mean=%.1fs" % (statistics.median(deltas), statistics.mean(deltas)))
print("games with >=1 snapshot: %d of %d" % (len(set(g for _,g in inplay) & set(by_gid)), len(gids_inplay)))

taut = 0; taut_tot = 0
for t,gid in inplay:
    arr = by_gid.get(gid)
    if not arr: continue
    lo,hi = arr[0][0], arr[-1][0]
    if lo <= t <= hi:
        taut_tot += 1
        if nearest(gid,t) <= 90: taut += 1
print("")
print("=== TAUTOLOGY CHECK ===")
print("odds rows INSIDE snapshot window: %d (%.1f%% of tip-defined in-play)" % (taut_tot, taut_tot/len(inplay)*100))
print("  of those, matched<=90s: %d/%d = %.1f%%" % (taut, taut_tot, taut/taut_tot*100))
print("odds rows OUTSIDE snapshot window (poller silent): %d" % (len(inplay)-taut_tot))

print("")
print("=== PER-GAME COVERAGE DEPTH ===")
counts=[]; q1=0; q4=0; complete=0; rows=[]
for gid,arr in by_gid.items():
    n=len(arr); counts.append(n)
    pers = set()
    for _,s in arr:
        try: pers.add(int(s["period"]))
        except Exception: pass
    has1 = 1 in pers; has4 = 4 in pers
    q1 += has1; q4 += has4
    first, last = arr[0][1], arr[-1][1]
    def clk(c):
        try:
            m,sec = c.split(":"); return int(m)*60+float(sec)
        except Exception: return None
    c0 = clk(first.get("clock","")); c1 = clk(last.get("clock",""))
    full = has1 and has4 and (c0 is not None and c0>=9*60) and (c1 is not None and c1<=60)
    complete += full
    rows.append((gid,n,sorted(pers),first.get("period"),first.get("clock"),last.get("period"),last.get("clock"),full))
counts.sort()
print("snapshots/game: min=%d p25=%d median=%.0f p75=%d max=%d" % (counts[0], counts[len(counts)//4], statistics.median(counts), counts[3*len(counts)//4], counts[-1]))
print("games containing a Q1 row: %d/%d" % (q1, len(by_gid)))
print("games containing a Q4 row: %d/%d" % (q4, len(by_gid)))
print("games with COMPLETE tip->final trace: %d/%d" % (complete, len(by_gid)))
print("")
print("gid          n   periods         first(P/clk)   last(P/clk)   complete")
for r in sorted(rows,key=lambda x:-x[1]):
    print("%s %4d  %-14s %2s/%-6s  %2s/%-6s   %s" % (r[0], r[1], str(r[2]), r[3], r[4], r[5], r[6], r[7]))

print("")
print("=== CONCENTRATION (game-level) ===")
contrib = sorted(per_game_tot.items(), key=lambda x:-x[1])
tot = sum(per_game_tot.values())
print("top games by odds-row share:")
for gid,c in contrib[:6]:
    m = per_game_match[gid]
    print("  %s: %d rows (%.1f%%)  matched %d (%.1f%%)" % (gid, c, c/tot*100, m, m/c*100))
top2 = sum(c for _,c in contrib[:2])
print("top-2 games = %.1f%% of all in-play odds rows" % (top2/tot*100))
rest_m = sum(per_game_match[g] for g,_ in contrib[2:]); rest_t = sum(c for _,c in contrib[2:])
print("drop top-2 -> coverage %d/%d = %.1f%%  (games left: %d)" % (rest_m, rest_t, rest_m/rest_t*100, len(contrib)-2))

gl = list(per_game_tot.keys())
boot=[]
for _ in range(20000):
    samp=[gl[random.randrange(len(gl))] for _ in gl]
    m=sum(per_game_match[g] for g in samp); t=sum(per_game_tot[g] for g in samp)
    if t: boot.append(m/t*100)
boot.sort()
print("")
print("=== GAME-BLOCK BOOTSTRAP (20k, resampling GAMES not rows) ===")
print("coverage%% point=%.1f  95%% CI=[%.1f, %.1f]" % (matched/len(inplay)*100, boot[int(.025*len(boot))], boot[int(.975*len(boot))]))

print("")
print("=== DESIGN EFFECT / n_eff ===")
series = collections.defaultdict(list)
for r in lines:
    if r.get("type")!="total" or r.get("alt")!="0": continue
    t=ts(r["ts"])
    if not t: continue
    parts=(r.get("teams") or "").split("|")
    abbr=frozenset(FULL.get(p.strip(),"?") for p in parts)
    cands=pair2gids.get(abbr)
    if not cands: continue
    best=None
    for tp,gid in cands:
        d=(t-tp).total_seconds()
        if 0<=d<=WIN_H*3600 and (best is None or d<best[0]): best=(d,gid)
    if not best: continue
    try: pts=float(r.get("points") or "")
    except Exception: continue
    series[best[1]].append((t,pts))
r1s=[]; lens=[]
for gid,arr in series.items():
    arr.sort(key=lambda x:x[0]); v=[p for _,p in arr]
    if len(v)<30: continue
    lens.append(len(v))
    mu=statistics.mean(v); var=statistics.pvariance(v)
    if var<=0: continue
    num=sum((v[i]-mu)*(v[i+1]-mu) for i in range(len(v)-1))
    r1s.append(num/((len(v)-1)*var))
if r1s:
    rbar=statistics.mean(r1s); mbar=statistics.mean(lens)
    deff=1+(mbar-1)*rbar
    print("lag-1 autocorr of main total within game: mean r1=%.4f (n_games=%d)" % (rbar, len(r1s)))
    print("mean obs/game=%.0f  DEFF=1+(m-1)*r1 = %.1f" % (mbar, deff))
    print("n_eff = %d/%.1f = %.0f quasi-independent obs" % (len(inplay), deff, len(inplay)/deff))
print("BUT the label-level unit is the GAME: n_independent = %d" % len(gids_inplay))

print("")
print("=== MINIMUM DETECTABLE EFFECT @ n=%d games ===" % len(gids_inplay))
n=len(gids_inplay)
print("two-sided a=.05, power .80: MDE = %.2f SD of a per-game statistic" % (2.8/math.sqrt(n)))
print("per-game ROI study at ~10%% SD/game: MDE ~= %.1f%% ROI" % (2.8*10/math.sqrt(n)))
print("half-width of 95%% CI on a win rate at n=%d: +-%.1fpp" % (n, 1.96*0.5/math.sqrt(n)*100))

pf = os.path.join(R,"elo_model","plays_full.csv")
if os.path.exists(pf):
    seen=set()
    with open(pf, encoding="utf-8-sig", newline="") as fh:
        rd=csv.DictReader(fh)
        col = "game_id" if "game_id" in (rd.fieldnames or []) else None
        for row in rd:
            if col: seen.add(row[col])
    ov = seen & set(by_gid)
    print("")
    print("=== plays_full.csv OVERLAP ===")
    print("plays_full games=%d  live-odds games=%d  INTERSECTION=%d" % (len(seen), len(by_gid), len(ov)))
