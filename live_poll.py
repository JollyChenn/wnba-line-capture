# live_poll.py - LIVE in-game data collector (cloud Actions job, runs during the nightly game window).
# Every ~75s while games are live: score/period/clock + team fouls/TO/reb + last-play + Pinnacle live
# game lines -> live_snapshots.csv / live_lines.csv. Gentle: 1 scoreboard + 1 summary per live game +
# 2 Pinnacle req per cycle. Commits every ~10 min. Exits when no live games (or 5h cap).
import json,urllib.request,csv,os,sys,time,datetime,subprocess
try:sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception:pass
UA={"User-Agent":"Mozilla/5.0"}
def getj(u):
    try:return json.load(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=15))
    except Exception:return {}
B="https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/"
def snap_lines():
    try:
        from curl_cffi import requests as creq
        PB="https://guest.api.arcadia.pinnacle.com/0.1";HK={"X-API-Key":"CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R","User-Agent":"Mozilla/5.0"}
        mm=creq.get(PB+"/sports/4/matchups",impersonate="chrome",timeout=15,headers=HK).json()
        mk=creq.get(PB+"/sports/4/markets/straight",impersonate="chrome",timeout=15,headers=HK).json()
        wn={m["id"]:"|".join(p.get("name","") for p in m.get("participants",[])) for m in mm
            if "wnba" in json.dumps(m.get("league",{})).lower() and not m.get("special")}
        rows=[]
        for x in mk:
            if x.get("matchupId") in wn and x.get("period")==0:
                pr=x.get("prices",[])
                rows.append([stamp,wn[x["matchupId"]],x.get("type"),x.get("side",""),
                             pr[0].get("points") if pr else None,",".join(str(p.get("price")) for p in pr[:2]),
                             1 if x.get("isAlternate") else 0])
        return rows
    except Exception:return []
new1=not os.path.exists("live_snapshots.csv");new2=not os.path.exists("live_lines.csv")
f1=open("live_snapshots.csv","a",newline="",encoding="utf-8");w1=csv.writer(f1)
f2=open("live_lines.csv","a",newline="",encoding="utf-8");w2=csv.writer(f2)
if new1:w1.writerow(["ts","game_id","period","clock","away","home","away_score","home_score",
                     "h_fouls","a_fouls","h_to","a_to","h_reb","a_reb","last_play"])
if new2:w2.writerow(["ts","teams","type","side","points","prices","alt"])
t0=time.time();idle=0;last_commit=time.time()
while time.time()-t0<5*3600 and idle<25:
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sb=getj(B+"scoreboard");live=[]
    for ev in sb.get("events",[]):
        c=(ev.get("competitions") or [{}])[0]
        if (((c.get("status") or {}).get("type") or {}).get("state") or "")=="in":live.append(ev)
    if not live:
        idle+=1;time.sleep(75);continue
    idle=0
    for ev in live:
        gid=str(ev["id"]);c=ev["competitions"][0];cs={x["homeAway"]:x for x in c["competitors"]}
        j=getj(B+"summary?event="+gid)
        tstat={}
        for tm in j.get("boxscore",{}).get("teams",[]):
            ab=tm.get("team",{}).get("abbreviation","")
            st={s.get("name"):s.get("displayValue") for s in tm.get("statistics",[])}
            tstat[ab]=(st.get("fouls",""),st.get("turnovers",""),st.get("totalRebounds",""))
        plays=j.get("plays",[])
        h=cs["home"]["team"]["abbreviation"];a=cs["away"]["team"]["abbreviation"]
        hf=tstat.get(h,("","",""));af=tstat.get(a,("","",""))
        w1.writerow([stamp,gid,(c.get("status") or {}).get("period"),
                     ((c.get("status") or {}).get("displayClock")),a,h,
                     cs["away"].get("score"),cs["home"].get("score"),
                     hf[0],af[0],hf[1],af[1],hf[2],af[2],
                     (plays[-1].get("text","")[:70] if plays else "")])
    for r in snap_lines():w2.writerow(r)
    f1.flush();f2.flush()
    if time.time()-last_commit>600:
        subprocess.run("git add -f live_snapshots.csv live_lines.csv && git commit -qm 'live snapshots' && git pull -q --rebase --autostash origin main && git push -q",shell=True)
        last_commit=time.time()
    time.sleep(75)
subprocess.run("git add -f live_snapshots.csv live_lines.csv && git commit -qm 'live snapshots (window end)' && git pull -q --rebase --autostash origin main && git push -q",shell=True)
print("live window done")
