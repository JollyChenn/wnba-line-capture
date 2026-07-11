# capture_gamelines.py - Pinnacle GAME lines (ML/spread/total) every capture cycle -> gamelines.csv.
# Change-dedup via gamelines_last.json. Gentle: 2 requests. Never fails the job (exit 0 always).
import json,csv,os,sys,datetime
try:sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception:pass
def main():
    from curl_cffi import requests as creq
    PB="https://guest.api.arcadia.pinnacle.com/0.1"
    HK={"X-API-Key":"CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R","User-Agent":"Mozilla/5.0"}
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mm=creq.get(PB+"/sports/4/matchups",impersonate="chrome",timeout=20,headers=HK).json()
    mk=creq.get(PB+"/sports/4/markets/straight",impersonate="chrome",timeout=20,headers=HK).json()
    wnba={m["id"]:m for m in mm if "wnba" in json.dumps(m.get("league",{})).lower() and not m.get("special")}
    last=json.load(open("gamelines_last.json")) if os.path.exists("gamelines_last.json") else {}
    rows=[]
    for x in mk:
        mid=x.get("matchupId")
        if mid not in wnba or x.get("period")!=0:continue
        m=wnba[mid];parts=m.get("participants",[])
        names="|".join(p.get("name","") for p in parts)
        start=(m.get("startTime") or "")[:16]
        typ=x.get("type");pr=x.get("prices",[])
        pts=pr[0].get("points") if pr else None
        prices=",".join(str(p.get("price")) for p in pr[:2])
        key=f"{mid}|{typ}|{x.get('side','')}|{pts}"
        val=prices
        if last.get(key)!=val:
            rows.append([stamp,mid,start,names,typ,x.get("side",""),pts,prices])
            last[key]=val
    if rows:
        new=not os.path.exists("gamelines.csv")
        with open("gamelines.csv","a",newline="",encoding="utf-8") as f:
            w=csv.writer(f)
            if new:w.writerow(["captured_utc","matchup_id","start","teams","type","side","points","prices"])
            w.writerows(rows)
        json.dump(last,open("gamelines_last.json","w"))
    print(f"gamelines: +{len(rows)} changed rows, {len(wnba)} games on board")
if __name__=="__main__":
    try:main()
    except Exception as e:print("gamelines error (ignored):",e)
    sys.exit(0)
