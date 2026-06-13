# scan_bets.py — scan ALL genuinely-upcoming WNBA games (ESPN status=pre), match our
# model picks to the live 1xbet lines, precise-fair + injury filter, and report bets
# GROUPED BY REAL GAME + tip time (UTC and MYT). Fixes the "lumped slate date" confusion.
import cloud_xbet as cx
import csv, datetime, json, urllib.request
from zoneinfo import ZoneInfo

MY = ZoneInfo("Asia/Kuala_Lumpur")
H = {"User-Agent": "Mozilla/5.0"}
now = datetime.datetime.now(datetime.timezone.utc)

# 1) ESPN upcoming games only (state == 'pre' = not started; real-time, ignores the lagging clock)
eg, seen = [], set()
for d in range(0, 3):
    day = (now + datetime.timedelta(days=d)).strftime("%Y%m%d")
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request(cx.ESPN + "?dates=" + day, headers=H), timeout=20))
    except Exception:
        continue
    for ev in j.get("events", []):
        if ev.get("status", {}).get("type", {}).get("state") != "pre":
            continue
        c = (ev.get("competitions") or [{}])[0].get("competitors", [])
        a = next((t for t in c if t.get("homeAway") == "away"), {})
        h = next((t for t in c if t.get("homeAway") == "home"), {})
        tip = datetime.datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        k = ((a.get("team") or {}).get("abbreviation"), (h.get("team") or {}).get("abbreviation"), tip)
        if k[0] and k[1] and k not in seen:
            seen.add(k)
            eg.append({"a": k[0], "h": k[1], "tip": tip})
eg.sort(key=lambda x: x["tip"])
print(f"{len(eg)} UPCOMING WNBA games (ESPN, not yet started):")
for g in eg:
    print(f"  {g['a']:>3}@{g['h']:<3}  {g['tip'].strftime('%a %b-%d %H:%MZ')}  =  {g['tip'].astimezone(MY).strftime('%a %b-%d %I:%M%p MYT')}")

# 2) model picks (validated markets; over = PRA only; drop disrupted) — latest slate only
picks = {}
_allrows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8")))
_latest = max((r["pick_date"] for r in _allrows), default="")
print(f"\n(model picks from latest slate {_latest})")
for r in _allrows:
    if r["pick_date"] != _latest:
        continue
    base = r["market"].split("_")[0]
    side = "Over" if r["market"].endswith("over") else "Under"
    if base not in cx.STAT_T or "disrupt" in r.get("signals", "").lower():
        continue
    if side == "Over" and base != "pra":
        continue
    picks.setdefault(r["player"].lower(), []).append(
        {"player": r["player"], "base": base, "side": side, "anchor": float(r["anchor"]),
         "proj": float(r["proj"]), "sd": float(r.get("sd") or 0), "fair": float(r["fair_odds"])})

# 3) pull 1xbet + injuries
inj = cx.injuries()
disc = cx.get(f"{cx.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={cx.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
if not disc:
    print("\n1xbet scrape blocked (Cloudflare) — retry in a minute."); raise SystemExit
allg = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]


def match(o1, o2):
    blob = f"{o1} {o2}".lower()
    for g in eg:
        ka = cx.TEAMKW.get(g["a"], [g["a"].lower()]); kh = cx.TEAMKW.get(g["h"], [g["h"].lower()])
        if all(any(w in blob for w in kw) for kw in (ka, kh)):
            return g
    return None


print("\n" + "=" * 72 + "\nBETS BY GAME (model x live 1xbet, precise-fair + injury gate)\n" + "=" * 72)
total = 0
for e in allg:
    g = match(e.get("O1", ""), e.get("O2", ""))
    if not g:
        continue
    mv = cx.get(cx.gz(e["I"]))
    sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
    stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
    props = {}
    if stat:
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
    bets = []
    for pkey, pks in picks.items():
        pp = props.get(pkey)
        if not pp:
            continue
        st = cx.status_of(pks[0]["player"], inj)
        side = pks[0]["side"]; cands = []
        for pk in pks:
            outs = pp.get((pk["base"], pk["side"]))
            if not outs:
                continue
            line, odds = min(outs, key=lambda t: abs(t[0] - pk["anchor"]))
            zone = (line >= pk["anchor"] - 1) if side == "Under" else (line <= pk["anchor"] + 1)
            if pk["sd"]:
                ph = cx._ncdf((line - pk["proj"]) / pk["sd"]); ph = ph if side == "Under" else 1 - ph
                fairL = 1 / max(ph, 0.02)
            else:
                fairL = pk["fair"]
            ev = odds / fairL - 1
            if odds > fairL and zone:
                strong = (line >= pk["anchor"]) if side == "Under" else (line <= pk["anchor"])
                cands.append((ev, pk["base"], line, odds, strong))
        if cands:
            ev, base, line, odds, strong = max(cands, key=lambda c: c[0])
            bets.append((ev, pks[0]["player"], base, side, line, odds, strong, st))
    if bets:
        print(f"\n{g['a']}@{g['h']}  {g['tip'].strftime('%a %b-%d %H:%MZ')} / {g['tip'].astimezone(MY).strftime('%a %I:%M%p MYT')}")
        for ev, player, base, side, line, odds, strong, st in sorted(bets, reverse=True):
            tag = "OUT-SKIP" if st == "OUT" else ("HOLD" if st == "HOLD" else ("STRONG" if strong else "ok"))
            total += 0 if st == "OUT" else 1
            print(f"   {player:18} {base.upper():4} {side:5} {line}@{odds}   EV {ev * 100:+5.0f}%   [{tag}]")
print(f"\n{total} actionable bet(s) across upcoming games.")
