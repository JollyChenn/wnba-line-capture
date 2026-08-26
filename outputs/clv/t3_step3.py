# TRACK 3 step 3: INDEPENDENT CLV recompute from xbet_board.csv (ignore stored columns)
import csv, os, sys, math, statistics, collections, random, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = r"C:\Users\Axioo\wnba-line-capture"
def ts(s):
    s=(s or "").replace("Z","+00:00")
    try: return datetime.datetime.fromisoformat(s)
    except Exception: return None

# --- games / tips / player->game
GM=list(csv.DictReader(open(os.path.join(D,"data","games_2026.csv"),encoding="utf-8")))
tipof={g["game_id"]:ts(g["tip"]) for g in GM}
dateof={g["game_id"]:g["date"] for g in GM}
pl_game={}
for r in csv.DictReader(open(os.path.join(D,"data","box_2026.csv"),encoding="utf-8")):
    gid=r["game_id"]
    if gid in dateof: pl_game[(r["player"].lower(),dateof[gid])]=gid

# --- board series
B=collections.defaultdict(list)   # (player,market,line) -> [(t, side, odds)]
for r in csv.DictReader(open(os.path.join(D,"xbet_board.csv"),encoding="utf-8")):
    t=ts(r["captured_utc"])
    if not t: continue
    try: ln=float(r["line"]); od=float(r["odds"])
    except: continue
    B[(r["player"].lower(),r["market"],ln)].append((t,r["side"],od))
for k in B: B[k].sort()
# two-sided snapshots per (player,market,line): time -> {side:odds}
SNAP=collections.defaultdict(dict)
for k,lst in B.items():
    d=collections.defaultdict(dict)
    for t,s,o in lst: d[t][s]=o
    SNAP[k]=dict(sorted(d.items()))
ALLLINES=collections.defaultdict(set)
for (p,m,ln) in B: ALLLINES[(p,m)].add(ln)

# --- bets_log first capture per graded key
caps=collections.defaultdict(list)
for b in csv.DictReader(open(os.path.join(D,"bets_log.csv"),encoding="utf-8")):
    d=b["date"].replace("-","")
    caps[(d,b["player"].lower(),b["market"],b["side"])].append((b["captured_utc"],float(b["line"]),float(b["odds"])))

R=list(csv.DictReader(open(os.path.join(D,"graded_bets.csv"),encoding="utf-8")))
def fnum(x):
    try: return float(x)
    except: return None

def vigfree(o_over,o_under,side):
    if not o_over or not o_under: return None
    a,b=1/o_over,1/o_under; s=a+b
    if s<=0: return None
    return (a/s) if side=="Over" else (b/s)

rows=[]
miss=collections.Counter()
for r in R:
    key=(r["date"],r["player"].lower(),r["market"],r["side"])
    cl=sorted(caps.get(key,[]))
    if not cl:
        # graded date is the resolved GAME date; bets_log may be keyed to the prior slate
        for dd in (r["date"],):
            pass
        miss["no_bets_log_key"]+=1
    gid=pl_game.get((r["player"].lower(),r["date"]))
    tip=tipof.get(gid) if gid else None
    if not tip: miss["no_tip"]+=1; continue
    p,m,side=r["player"].lower(),r["market"],r["side"]
    oline,oodds=float(r["line"]),float(r["odds"])
    # ENTRY instant: first bets_log capture if available else first board quote at our line before tip
    ent_t=ts(cl[0][0]) if cl else None
    sn=SNAP.get((p,m,oline),{})
    pre=[(t,v) for t,v in sn.items() if t<tip]
    if not pre: miss["no_board_at_our_line_pretip"]+=1; continue
    if ent_t is None: ent_t=pre[0][0]
    # entry two-sided at our line at/nearest-before entry instant
    ecand=[(t,v) for t,v in pre if t<=ent_t+datetime.timedelta(minutes=45)]
    if not ecand: ecand=[pre[0]]
    et,ev=ecand[-1][0],ecand[-1][1]
    p_ent=vigfree(ev.get("Over"),ev.get("Under"),side)
    # CLOSE at our line = last two-sided quote before tip AT OUR LINE
    ct,cv=pre[-1]
    p_cl_same=vigfree(cv.get("Over"),cv.get("Under"),side)
    close_odds_same=cv.get(side)
    # TRUE CLOSE = last two-sided quote before tip at ANY line for this player/market
    best=None
    for ln in ALLLINES.get((p,m),()):
        s2=SNAP.get((p,m,ln),{})
        pp=[(t,v) for t,v in s2.items() if t<tip and "Over" in v and "Under" in v]
        if pp and (best is None or pp[-1][0]>best[0]): best=(pp[-1][0],ln,pp[-1][1])
    rows.append(dict(g=r,gid=gid,tip=tip,ent_t=et,oline=oline,oodds=oodds,side=side,
                     p_ent=p_ent, ct=ct, close_odds_same=close_odds_same, p_cl_same=p_cl_same,
                     true_close=best, stored_odds_clv=fnum(r["odds_clv"]),
                     stored_line_clv=fnum(r["line_clv"]), pnl=float(r["pnl"]) if r["result"] in("WIN","loss") else None))
print("matched rows:",len(rows),"| misses:",dict(miss))

# lag between our-line close and tip vs true close and tip
lagsame=[(x["tip"]-x["ct"]).total_seconds()/3600 for x in rows]
lagtrue=[(x["tip"]-x["true_close"][0]).total_seconds()/3600 for x in rows if x["true_close"]]
print(f"hours before tip:  last quote AT OUR LINE  median {statistics.median(lagsame):.2f}h  mean {statistics.mean(lagsame):.2f}h")
print(f"hours before tip:  TRUE last quote any line median {statistics.median(lagtrue):.2f}h  mean {statistics.mean(lagtrue):.2f}h")
moved=sum(1 for x in rows if x["true_close"] and abs(x["true_close"][1]-x["oline"])>1e-6)
print(f"line moved away from our line before tip: {moved}/{len(rows)} ({moved/len(rows)*100:.1f}%)")
gap=[(x["true_close"][0]-x["ct"]).total_seconds()/3600 for x in rows if x["true_close"] and abs(x["true_close"][1]-x["oline"])>1e-6]
if gap: print(f"  in those, stored 'close' is a median {statistics.median(gap):.2f}h EARLIER than the true close")

# --- INDEPENDENT odds-CLV at our line, vs stored
ind=[]; both=[]
for x in rows:
    if x["close_odds_same"] and x["oodds"]:
        v=x["oodds"]/x["close_odds_same"]-1; x["ind_odds_clv"]=v; ind.append(v)
        if x["stored_odds_clv"] is not None: both.append((v,x["stored_odds_clv"]))
def corr(xs,ys):
    mx=statistics.mean(xs);my=statistics.mean(ys)
    num=sum((a-mx)*(b-my) for a,b in zip(xs,ys)); den=math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    return num/den if den else float('nan')
print(f"\nindependent odds-CLV (our line, last pre-tip quote): n={len(ind)} mean {statistics.mean(ind)*100:+.2f}%  median {statistics.median(ind)*100:+.2f}%")
if both:
    agree=sum(1 for a,b in both if abs(a-b)<1e-9)
    print(f"  vs stored odds_clv: n={len(both)} corr={corr([a for a,b in both],[b for a,b in both]):+.3f} exact-agree {agree}/{len(both)} ({agree/len(both)*100:.1f}%)")
    print(f"  stored mean {statistics.mean([b for a,b in both])*100:+.2f}%  independent mean {statistics.mean([a for a,b in both])*100:+.2f}%")

# --- the ECONOMICALLY MEANINGFUL CLV: EV under the closing vig-free probability, at our line
ev=[]
for x in rows:
    if x["p_cl_same"] is not None:
        x["ev_close"]=x["p_cl_same"]*x["oodds"]-1; ev.append(x)
print(f"\nEV vs 1xbet's OWN vig-free close at our line: n={len(ev)} mean {statistics.mean([x['ev_close'] for x in ev])*100:+.2f}%")
# and entry-instant vig-free EV (should be ~ -margin/2 by construction)
e2=[x for x in rows if x["p_ent"] is not None]
print(f"EV vs 1xbet's OWN vig-free price AT ENTRY:     n={len(e2)} mean {statistics.mean([x['p_ent']*x['oodds']-1 for x in e2])*100:+.2f}%  (= -half the board margin, sanity check)")

# save joined rows for step 4/5
import pickle
with open(os.path.join(D,"outputs","clv","joined.pkl"),"wb") as f:
    pickle.dump([{k:(v if not isinstance(v,datetime.datetime) else v.isoformat()) for k,v in x.items() if k!="g"} | {"g":x["g"]} for x in rows], f)
