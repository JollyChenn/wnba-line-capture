# Builds the master bet table T. exec()'d by the analysis scripts.
import os
D_=os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D_,"xm_build.py"),encoding="utf-8").read())
import datetime, statistics, collections
H=lambda h: datetime.timedelta(hours=h)

ANCHOR_H = 12.0     # "early" observation
GATE_H   = 6.0      # decision + pricing instant (card pings ~6h out)

def novig(a,b):
    if a is None or b is None or a<=1 or b<=1: return None
    pa,pb=1/a,1/b
    return pa/(pa+pb)

# --- Pinnacle game-market state at a moment ---
def pinn_state(gid, when):
    out={}
    t=at_or_before(PT.get(gid,[]), when)
    if t: out["tot"]=t[1]; out["tot_p"]=t[2]
    s=at_or_before(PS.get(gid,[]), when)
    if s: out["spr"]=s[1]
    m=at_or_before(PM.get(gid,[]), when)
    if m: out["mlh"]=m[1]
    return out

T=[]
skip=collections.Counter()
for (pl,mk,gid),ser in PROP.items():
    tp_raw = gmeta[gid][1]; tp=aware(tp_raw)
    now = pgrow.get((pl, tp_raw))
    if not now: skip["nobox"]+=1; continue
    if now["min"] < 8: skip["dnp"]+=1; continue
    q6 = two_sided_at(pl,mk,gid, tp-H(GATE_H))
    if not q6: skip["no6"]+=1; continue
    cap6, line6, ood6, uod6 = q6
    if now[mk] == line6: skip["push"]+=1; continue
    qA = two_sided_at(pl,mk,gid, tp-H(ANCHOR_H))
    lineA = qA[1] if qA else None
    oodA  = qA[2] if qA else None
    capA  = qA[0] if qA else None
    # one-sided anchor fallback (Over only) - more coverage for the line-move feature
    ovA = at_or_before(ser["Over"], tp-H(ANCHOR_H))
    lineA1 = ovA[1] if ovA else None
    oodA1  = ovA[2] if ovA else None
    g6 = pinn_state(gid, tp-H(GATE_H)); gA = pinn_state(gid, tp-H(ANCHOR_H))
    hm, aw = gmeta[gid][2], gmeta[gid][3]
    tmm = now["tm"]; is_home = (tmm==hm)
    T.append(dict(pl=pl, mk=mk, gid=gid, tip=tp, date=gmeta[gid][0], tm=tmm, home=is_home,
        line=line6, ood=ood6, uod=uod6, cap6=cap6,
        p_over=novig(ood6,uod6),
        actual=now[mk], over_won=now[mk]>line6, minutes=now["min"],
        lineA=lineA, oodA=oodA, capA=capA, lineA1=lineA1, oodA1=oodA1,
        dline=(None if lineA is None else line6-lineA),
        dline1=(None if lineA1 is None else line6-lineA1),
        dood1=(None if oodA1 is None else ood6-oodA1),
        tot6=g6.get("tot"), totA=gA.get("tot"),
        totp6=g6.get("tot_p"), totpA=gA.get("tot_p"),
        spr6=g6.get("spr"), sprA=gA.get("spr"), mlh=g6.get("mlh"),
        prevline=prevline.get((pl,mk,tp_raw)),
    ))
for r in T:
    r["dtot"] = None if (r["tot6"] is None or r["totA"] is None) else r["tot6"]-r["totA"]
    # signed spread from HER team's perspective: negative = she is favoured
    if r["spr6"] is not None and r["sprA"] is not None:
        s6 = r["spr6"] if r["home"] else -r["spr6"]
        sA = r["sprA"] if r["home"] else -r["sprA"]
        r["hspr6"]=s6; r["dspr"]=s6-sA
        r["dabsspr"]=abs(r["spr6"])-abs(r["sprA"])
    else:
        r["hspr6"]=None; r["dspr"]=None; r["dabsspr"]=None
    r["notraised"] = None if r["prevline"] is None else (r["line"]-r["prevline"] < 0.5)

def pnl(r, sd):
    if sd=="Over":  return (r["ood"]-1) if r["over_won"] else -1.0
    else:           return (r["uod"]-1) if not r["over_won"] else -1.0
