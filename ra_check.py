# ra_check.py — pull tonight's LIVE 1xbet RA lines, run the precise-fair check.
# Answers "is RA actually +EV, or is the juice eating the high hit rate?"
import csv, datetime
from zoneinfo import ZoneInfo
import cloud_xbet as cx

utc_d = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
la_d = datetime.datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()
print(f"UTC date={utc_d}  LA slate date={la_d}" + ("   <-- MISMATCH (cloud uses UTC!)" if utc_d != la_d else ""))

allrows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8")))
slate = la_d if any(r["pick_date"] == la_d for r in allrows) else max(r["pick_date"] for r in allrows)
ra = {r["player"].lower(): r for r in allrows if r["pick_date"] == slate and r["market"] == "ra_under"}
print(f"\nslate {slate}: {len(ra)} RA-under pick(s)")
for r in ra.values():
    print(f"  {r['player']}: median~{r['anchor']}  proj {r['proj']}  sd {r['sd']}  (model fair {r['fair_odds']})")
if not ra:
    print("  (no RA signal on this slate — nothing to check)"); raise SystemExit

near = cx.espn_near(3000)
teams = set(t for a, h, _ in near for t in (a, h) if t)
nearkw = [cx.TEAMKW.get(t, [t.lower()]) for t in teams]
print(f"\n{len(near)} game(s) tonight; pulling 1xbet boards...")
disc = cx.get(f"{cx.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={cx.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
if not disc:
    print("1xbet scrape blocked (Cloudflare) — try again shortly."); raise SystemExit
games = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
target = [e for e in games if any(all(w in f"{e.get('O1','')} {e.get('O2','')}".lower() for w in kw) for kw in nearkw)]
props = {}
for e in target:
    mv = cx.get(cx.gz(e["I"]))
    sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
    stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
    if not stat:
        continue
    val = (cx.get(cx.gz(stat["I"])) or {}).get("Value", {}) or {}

    def walk(o):
        if isinstance(o, dict):
            pl = o.get("PL"); T = o.get("T")
            if isinstance(pl, dict) and T in cx.T2S and o.get("P") is not None and o.get("C"):
                stt, sdd = cx.T2S[T]
                props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((stt, sdd), []).append((float(o["P"]), float(o["C"])))
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(val)
print(f"players on boards: {len(props)}")

print(f"\n{'player':18}{'RA-U line@odds':16}{'proj':>6}{'P(und)':>8}{'fair':>7}{'EV':>8}  verdict")
print("-" * 80)
any_line = False
for key, r in ra.items():
    pp = props.get(key)
    outs = pp.get(("ra", "Under")) if pp else None
    if not outs:
        print(f"{r['player']:18}{'-- not posted':16}   (RA is often star-only / posts late)"); continue
    any_line = True
    anchor, proj, sd = float(r["anchor"]), float(r["proj"]), float(r["sd"] or 3.0)
    line, odds = min(outs, key=lambda t: abs(t[0] - anchor))
    p_und = cx._ncdf((line - proj) / sd)
    fair = 1 / max(p_und, 0.02)
    ev = odds / fair - 1
    verdict = "OK +EV BET" if ev > 0.02 else ("~flat" if ev > -0.02 else "JUICED AWAY (skip)")
    print(f"{r['player']:18}{f'{line}@{odds}':16}{proj:>6.1f}{p_und:>8.1%}{fair:>7.2f}{ev * 100:>+7.1f}%  {verdict}")
if not any_line:
    print("\n(no RA line posted for our signal players — exactly the 'star-only/late' availability problem)")
