import csv, os, sys, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(D)
def load(p):
    with open(p, encoding="utf-8-sig", newline="") as fh: return list(csv.DictReader(fh))
def ts(s):
    s=(s or "").strip().replace("Z","")
    for f in ("%Y-%m-%dT%H:%M:%S","%Y-%m-%dT%H:%M"):
        try: return datetime.datetime.strptime(s,f)
        except Exception: pass
    return None

lines = load(os.path.join(R,"live_lines.csv"))
names = collections.Counter()
for r in lines:
    for p in (r.get("teams") or "").split("|"): names[p.strip()] += 1
print("=== DISTINCT TEAM STRINGS IN live_lines ===")
for k,v in sorted(names.items(), key=lambda x:-x[1]): print("  %-30s %d" % (k,v))

snaps = load(os.path.join(R,"live_snapshots.csv"))
by_gid = collections.defaultdict(list)
for s in snaps:
    t = ts(s["ts"])
    if t: by_gid[s["game_id"]].append((t,s))
for k in by_gid: by_gid[k].sort(key=lambda x:x[0])

games = load(os.path.join(R,"data","games_2026.csv"))
gm = {g["game_id"]:g for g in games}
print("")
print("=== ARE ALL 27 SNAPSHOT GAMES IN games_2026.csv? ===")
missing=[g for g in by_gid if g not in gm]
print("snapshot game_ids missing from games_2026.csv: %d -> %s" % (len(missing), missing))

# snapshot-derived window per game -> count odds rows by team abbr match
FULL = {"Atlanta Dream":"ATL","Chicago Sky":"CHI","Connecticut Sun":"CON","Dallas Wings":"DAL",
        "Golden State Valkyries":"GS","Indiana Fever":"IND","Las Vegas Aces":"LV",
        "Los Angeles Sparks":"LA","Minnesota Lynx":"MIN","New York Liberty":"NY",
        "Phoenix Mercury":"PHO","Seattle Storm":"SEA","Washington Mystics":"WSH"}
# build odds rows keyed by abbr-pair and time
rows_by_pair = collections.defaultdict(list)
for r in lines:
    t = ts(r["ts"])
    if not t: continue
    ab = frozenset(FULL.get(p.strip(),p.strip()) for p in (r.get("teams") or "").split("|"))
    rows_by_pair[ab].append(t)
for k in rows_by_pair: rows_by_pair[k].sort()

print("")
print("=== PER-GAME: odds rows inside SNAPSHOT window (snapshot-derived, the claim's own definition) ===")
tot=0; totm=0
per=[]
for gid,arr in by_gid.items():
    aw = arr[0][1]["away"]; hm = arr[0][1]["home"]
    ab = frozenset([aw,hm])
    lo,hi = arr[0][0], arr[-1][0]
    cand = rows_by_pair.get(ab, [])
    ins = [t for t in cand if lo <= t <= hi]
    stimes=[x[0] for x in arr]
    m=0; ds=[]
    for t in ins:
        d=min(abs((t-s).total_seconds()) for s in stimes); ds.append(d)
        if d<=90: m+=1
    span=(hi-lo).total_seconds()/60.0
    tot+=len(ins); totm+=m
    per.append((gid,aw,hm,len(arr),len(ins),m,span))
for p in sorted(per,key=lambda x:-x[4]):
    print("  %s %3s@%-3s snaps=%3d oddsrows=%5d matched90=%5d span=%.0fmin" % p)
print("TOTAL odds rows inside snapshot windows=%d matched=%d (%.1f%%)" % (tot,totm,totm/max(tot,1)*100))
print("games contributing: %d" % len(per))

# span stats
spans=[p[6] for p in per]
spans.sort()
print("")
print("=== WINDOW SPAN (min) per game: min=%.0f median=%.0f max=%.0f ===" % (spans[0],statistics.median(spans),spans[-1]))
print("a full WNBA game is ~110-125 real minutes; count with span>=100: %d/%d" % (sum(1 for s in spans if s>=100), len(spans)))

# identical ts strings check
lts=set(r["ts"] for r in lines); sts=set(s["ts"] for s in snaps)
print("")
print("=== SAME-POLLER EVIDENCE ===")
print("snapshot ts strings also present verbatim in live_lines: %d/%d (%.1f%%)" % (len(sts&lts), len(sts), len(sts&lts)/len(sts)*100))
print("live_lines min ts=%s max ts=%s" % (min(lts), max(lts)))
print("snapshots  min ts=%s max ts=%s" % (min(sts), max(sts)))
