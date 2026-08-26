import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

def nd(s): return (s or "").replace("-","")[:8]
G = load("graded_bets.csv"); L = load("bets_log.csv")

# --- bets_log index: (date, player, market, side) -> rows sorted by capture
li = collections.defaultdict(list)
for r in L:
    t = ts(r["captured_utc"])
    if t: li[(nd(r["date"]), (r["player"] or "").lower(), r["market"], r["side"])].append((t, r))
for v in li.values(): v.sort(key=lambda z: z[0])

# --- raw board index: (pl, mk, side, line) -> [(t, odds)]
bi = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None:
        bi[((b.get("player") or "").lower(), b.get("market"), b.get("side"), ln)].append((t, o))
for v in bi.values(): v.sort(key=lambda z: z[0])

dt2tip = collections.defaultdict(list)
for (pl,tp),row in pgrow.items(): dt2tip[(pl,row["date"])].append(tp)

miss = collections.Counter(); OUT=[]
for r in G:
    pl=(r["player"] or "").lower(); d=nd(r["date"]); mk=r["market"]; sd=r["side"]; ln=f(r["line"])
    od=f(r["odds"]); act=f(r["actual"])
    if ln is None or od is None: miss["badrow"]+=1; continue
    tps = dt2tip.get((pl,d))
    if not tps: miss["no_box"]+=1; continue
    gt = tps[0]
    # capture time from log
    rows = li.get((d,pl,mk,sd), [])
    exact=[z for z in rows if f(z[1]["line"])==ln]
    src_rows = exact or rows
    T = src_rows[0][0] if src_rows else None
    tier = r.get("tier") or (src_rows[0][1]["tier"] if src_rows else "")
    ev = f(src_rows[0][1]["ev"]) if src_rows else None
    pinn = f(src_rows[0][1].get("pinn")) if src_rows else None
    if T is None: T = gt - datetime.timedelta(hours=6); miss["no_log_time"]+=1
    opp = "Under" if sd=="Over" else "Over"
    cand = [z for z in bi.get((pl,mk,opp,ln),[]) if z[0] <= gt and (gt-z[0]).total_seconds()<=60*3600]
    if not cand: miss["no_opp_quote"]+=1; oppod=None
    else: oppod = min(cand, key=lambda z: abs((z[0]-T).total_seconds()))[1]
    if act is None: miss["no_actual"]+=1; continue
    if act == ln: miss["push"]+=1; continue
    over_won = act > ln
    won = over_won if sd=="Over" else (not over_won)
    if (r["result"]=="WIN") != won: miss["result_mismatch"]+=1
    OUT.append(dict(date=d, pl=pl, mk=mk, sd=sd, ln=ln, od=od, oppod=oppod, act=act,
                    over_won=over_won, won=won, src=r["src"], tier=tier, ev=ev, pinn=pinn,
                    gt=gt.isoformat(), T=T.isoformat()))
print("built", len(OUT), "miss", dict(miss))
print("with opp quote", sum(1 for x in OUT if x["oppod"]), "by src",
      collections.Counter(x["src"] for x in OUT if x["oppod"]))
print("opp odds dist", statistics.median([x["oppod"] for x in OUT if x["oppod"]]))
# sanity: emitted+opp implied margin
mg=[1/x["od"]+1/x["oppod"]-1 for x in OUT if x["oppod"]]
print("median board margin", round(100*statistics.median(mg),2),"%  n=",len(mg))
w=csv.DictWriter(open(os.path.join(D,"fam_bets.csv"),"w",newline="",encoding="utf-8"),fieldnames=list(OUT[0].keys()))
w.writeheader(); w.writerows(OUT)
