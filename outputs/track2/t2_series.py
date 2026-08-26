# Build per-game in-play series: main-line prices, devigged, plus ladder-derived fair lines.
import csv,os,sys,math,statistics,datetime,collections,pickle
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
D=r"C:\Users\Axioo\wnba-line-capture"; OUT=os.path.join(D,"outputs","track2")
def f(x):
    try: return float(x)
    except (TypeError,ValueError): return None
def am(p):
    v=f(p)
    if v is None: return None
    return (-v)/((-v)+100) if v<0 else 100/(v+100)
def dec(p):
    v=f(p)
    if v is None: return None
    return 1+ (100/(-v) if v<0 else v/100)
inwin=pickle.load(open(os.path.join(OUT,"inwin.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))

def pair(pr):
    s=(pr or "").split(",")
    if len(s)!=2: return None
    a,b=am(s[0]),am(s[1])
    if a is None or b is None or a+b<=0: return None
    return a/(a+b), a+b   # devigged first-side prob, and overround

SER={}   # gid -> dict of series name -> list of (elapsed_min, value, raw)
LAD={}   # gid -> list of (el, market, fairline)
vigs=collections.defaultdict(list)
for gid,rows in inwin.items():
    snaps=collections.defaultdict(list)
    for x in rows: snaps[x["el"]].append(x["row"])
    s=collections.defaultdict(list)
    for el in sorted(snaps):
        rs=snaps[el]
        for r in rs:
            tp=r["type"]; alt=r["alt"]=="1"; pts=f(r["points"]); pv=pair(r["prices"])
            if pv is None: continue
            p,ov=pv
            if alt: continue
            if tp=="moneyline":
                s["ml_p"].append((el,p)); vigs["moneyline"].append(ov)
            elif tp=="spread":
                s["sp_line"].append((el,pts)); s["sp_p"].append((el,p)); vigs["spread"].append(ov)
            elif tp=="total":
                s["tot_line"].append((el,pts)); s["tot_p"].append((el,p)); vigs["total"].append(ov)
            elif tp=="team_total":
                k="tth" if r["side"]=="home" else "tta"
                s[k+"_line"].append((el,pts)); s[k+"_p"].append((el,p)); vigs["team_total"].append(ov)
        # ladder fair lines (main+alt together): interpolate points where devig prob = 0.5
        for tp,key in (("spread","sp_fair"),("total","tot_fair")):
            lad=[]
            for r in rs:
                if r["type"]!=tp: continue
                pts=f(r["points"]); pv=pair(r["prices"])
                if pts is None or pv is None: continue
                lad.append((pts,pv[0]))
            if len(lad)<2: continue
            lad.sort()
            # prob is monotone decreasing in points for both (home cover / over)
            fair=None
            for i in range(len(lad)-1):
                x1,y1=lad[i]; x2,y2=lad[i+1]
                if (y1-0.5)*(y2-0.5)<=0 and y1!=y2:
                    fair=x1+(y1-0.5)*(x2-x1)/(y1-y2); break
            if fair is None:
                # extrapolate from nearest edge using local slope
                if abs(lad[0][1]-0.5)<abs(lad[-1][1]-0.5): x1,y1=lad[0]; x2,y2=lad[1]
                else: x1,y1=lad[-2]; x2,y2=lad[-1]
                if y1!=y2: fair=x1+(y1-0.5)*(x2-x1)/(y1-y2)
            if fair is not None and abs(fair)<400: s[key].append((el,fair))
    SER[gid]=dict(s)
print("VIG / overround by market (median, n):")
for k,v in vigs.items(): print("  %-11s %.4f  n=%d"%(k,statistics.median(v),len(v)))
print()
print("series coverage (games with >=30 points):")
allk=set()
for s in SER.values(): allk|=set(s)
for k in sorted(allk):
    g=[gid for gid in SER if len(SER[gid].get(k,[]))>=30]
    tot=sum(len(SER[gid].get(k,[])) for gid in SER)
    print("  %-10s games=%2d  obs=%d"%(k,len(g),tot))
# sampling gap
gaps=[]
for gid,s in SER.items():
    els=sorted(set(e for e,_ in s.get("tot_line",[])))
    gaps+= [b-a for a,b in zip(els,els[1:])]
print("\nmedian sampling gap (min): %.2f  p90 %.2f  n=%d"%(statistics.median(gaps),sorted(gaps)[int(.9*len(gaps))],len(gaps)))
# elapsed coverage
els=[e for s in SER.values() for e,_ in s.get("tot_line",[])]
print("elapsed min: min %.1f max %.1f  median %.1f"%(min(els),max(els),statistics.median(els)))
h=collections.Counter(int(e//10)*10 for e in els)
print("obs by 10-min bucket:",dict(sorted(h.items())))
pickle.dump(SER,open(os.path.join(OUT,"ser.pkl"),"wb"))
