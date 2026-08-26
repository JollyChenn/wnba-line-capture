import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
random.seed(20260826)
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, "mega_sweep.py"), encoding="utf-8").read()
     .split('print(f"{len(B)} two-sided board quotes')[0])

print("BOARD B:", len(B))
# ---- parse gamelines into per-capture snapshots ----
rows = load("gamelines.csv")
print("gamelines rows", len(rows))
snap = collections.defaultdict(lambda: collections.defaultdict(list))  # (mid,cap) -> type -> rows
meta = {}
for r in rows:
    mid = r.get("matchup_id"); cap = ts(r.get("captured_utc"))
    if not cap: continue
    snap[(mid, cap)][r.get("type")].append(r)
    tmn = (r.get("teams") or "").split("|")
    if len(tmn) == 2:
        meta[mid] = (r.get("start"), tmn[0].strip(), tmn[1].strip())
print("distinct matchup_id", len(meta), "snapshots", len(snap))
# how many team_total rows per capture
c = collections.Counter(len(v.get("team_total", [])) for v in snap.values())
print("team_total rows per snapshot:", dict(c))
c = collections.Counter(len(v.get("spread", [])) for v in snap.values())
print("spread rows per snapshot:", dict(sorted(c.items())[:8]), "...")
c = collections.Counter(len(v.get("moneyline", [])) for v in snap.values())
print("ml rows per snapshot:", dict(c))

# home/away check: does teams[0] == home in games_2026?
gm_by_date_pair = {}
for gid,(dt,tp,hm,aw) in gmeta.items():
    gm_by_date_pair[(dt, tuple(sorted((hm,aw))))] = (hm,aw,tp,gid)
ok=bad=miss=0
for mid,(start,t0,t1) in meta.items():
    d = (start or "")[:10].replace("-","")
    a0,a1 = FULL.get(t0,""), FULL.get(t1,"")
    if not a0 or not a1: miss+=1; continue
    k=(d, tuple(sorted((a0,a1))))
    if k not in gm_by_date_pair:
        # try +1 day (UTC start vs local date)
        try:
            dd=(datetime.date(int(d[:4]),int(d[4:6]),int(d[6:]))+datetime.timedelta(days=1)).strftime("%Y%m%d")
        except Exception: dd=None
        k2=(dd,tuple(sorted((a0,a1)))) if dd else None
        if k2 and k2 in gm_by_date_pair: k=k2
        else: miss+=1; continue
    hm,aw,tp,gid = gm_by_date_pair[k]
    if hm==a0: ok+=1
    else: bad+=1
print(f"teams[0]==home: {ok}  teams[0]==away: {bad}  unmatched: {miss}")

# spread sign: is 'points' the home spread?
print("--- sample spread/ml alignment ---")
n=0
for (mid,cap),v in sorted(snap.items(), key=lambda x:x[0][1]):
    if "spread" in v and "moneyline" in v and n<5:
        start,t0,t1 = meta[mid]
        mlr=v["moneyline"][0]; pr=(mlr.get("prices") or "").split(",")
        sps=sorted(v["spread"], key=lambda r: abs((am((r.get('prices') or ',').split(',')[0]) or 0)-(am((r.get('prices') or ',').split(',')[1]) or 0)))
        print(t0,"|",t1,"ML",pr,"mainspread",sps[0].get("points"),sps[0].get("prices"))
        n+=1
