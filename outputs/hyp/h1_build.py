# Reconstruct per-player H1 points from play-by-play, validate against data/halves_2026.csv,
# then write outputs/hyp/h1_all.csv covering every game the PBP has.
import os, sys, csv, re, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib; ROOT = hlib.boot(globals())
random.seed(20260826)

MK = re.compile(r"^(.+?) makes (.+)$")
P = collections.defaultdict(lambda: collections.defaultdict(float))  # (gid,player)->{h1,h2,tot}
seen_g = set()
for r in load("elo_model/plays_full.csv"):
    gid = r["game_id"]; seen_g.add(gid)
    try: per = int(r["period"])
    except Exception: continue
    t = r["text"] or ""
    m = MK.match(t)
    if not m: continue
    who = m.group(1).strip().lower(); tail = m.group(2).lower()
    if "three point" in tail: v = 3
    elif "free throw" in tail: v = 1
    else: v = 2
    k = (gid, who)
    P[k]["h1" if per <= 2 else "h2"] += v
    P[k]["tot"] += v

print("pbp games", len(seen_g), "player-games with points", len(P))

# validate vs halves_2026 on its window, and vs box pts everywhere
Hf = {}
for r in load("data/halves_2026.csv"):
    Hf[(r["game_id"], r["player"].strip().lower())] = (f(r["h1_pts"]), f(r["h2_pts"]), f(r["pts"]))
ov = [(k, P[k], Hf[k]) for k in P if k in Hf]
exact_h1 = sum(1 for k, p, h in ov if p["h1"] == h[0])
exact_tot = sum(1 for k, p, h in ov if p["tot"] == h[2])
print(f"overlap with halves_2026: {len(ov)} player-games  h1 exact {exact_h1} ({exact_h1/max(1,len(ov)):.3%})  tot exact {exact_tot} ({exact_tot/max(1,len(ov)):.3%})")
if ov:
    d = [p["h1"]-h[0] for k,p,h in ov]
    print("  h1 diff mean %.3f sd %.3f  |diff|>0 count %d" % (statistics.mean(d), statistics.pstdev(d), sum(1 for x in d if x)))

# validate total vs box for ALL pbp games in gmeta
bx = 0; bx_ok = 0
for (gid, who), v in P.items():
    if gid not in gmeta: continue
    tp = gmeta[gid][1]
    row = pgrow.get((who, tp))
    if not row: continue
    bx += 1
    if row["pts"] == v["tot"]: bx_ok += 1
print(f"vs box_2026 totals: {bx} matched player-games, exact {bx_ok} ({bx_ok/max(1,bx):.3%})")

# write union file: prefer halves_2026 (authoritative), fill with pbp
out = []
keys = set(Hf) | set(P.keys())
for gid, who in sorted(keys):
    if (gid, who) in Hf:
        h1, h2, tt = Hf[(gid, who)]; src = "halves"
    else:
        v = P[(gid, who)]; h1, h2, tt = v["h1"], v["h2"], v["tot"]; src = "pbp"
    dt = gmeta[gid][0] if gid in gmeta else ""
    out.append(dict(game_id=gid, date=dt, player=who, h1=h1, h2=h2, pts=tt, src=src))
fp = os.path.join(ROOT, "outputs", "hyp", "h1_all.csv")
with open(fp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["game_id","date","player","h1","h2","pts","src"]); w.writeheader(); w.writerows(out)
print("wrote", fp, len(out), "rows;  games:", len(set(r['game_id'] for r in out)))
dd = sorted(set(r["date"] for r in out if r["date"]))
print("date range", dd[0], dd[-1])

# how much of the BOARD window has H1 coverage?
have = set()
for r in out:
    if r["game_id"] in gmeta: have.add((r["player"], gmeta[r["game_id"]][1]))
btips = sorted(set(gt for (pl,mk,gt) in side if mk=="pts"))
cov = collections.Counter()
for (pl,mk,gt), sd in side.items():
    if mk != "pts" or "Over" not in sd or "Under" not in sd: continue
    cov["quotes"] += 1
    if (pl, gt) in have: cov["with_h1"] += 1
print("two-sided pts quotes:", cov["quotes"], " with H1 known for THAT game:", cov["with_h1"])
