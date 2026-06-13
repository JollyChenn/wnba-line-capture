# ============================================================================
# cloud_xbet.py — CLOUD 1xbet capture via 1x-bet.com (laptop-off, no browser).
# ANTI-FLAG: ESPN pre-gate (FREE) decides if a game is near tip; we touch 1x-bet.com
# ONLY then. If Cloudflare blocks the scrape -> ping the model PROJECTIONS so you can
# check 1xbet manually. Each scheduled run is usually a fresh GitHub IP (rotation).
# ============================================================================
import os, sys, csv, json, time, datetime, urllib.request
from collections import defaultdict
from curl_cffi import requests as creq
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://1x-bet.com/service-api"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
CHAMP = "2874802"
WINDOW = int(os.environ.get("XBET_WINDOW_MIN", "180"))
PICKS, SNAP = "picks_log.csv", "xbet_snapshots.csv"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
STAT_T = {"pts": (1807, 1806), "pr": (5671, 5672), "pa": (5673, 5674),
          "ra": (7141, 7142), "pra": (16427, 16428)}
T2S = {}
for _s, (_o, _u) in STAT_T.items():
    T2S[_o] = (_s, "Over"); T2S[_u] = (_s, "Under")
TEAMKW = {"SEA": ["seattle", "storm"], "GS": ["golden state", "valkyr"], "TOR": ["toronto", "tempo"],
          "WSH": ["washington", "mystic"], "NY": ["new york", "liberty"], "CON": ["connecticut", "sun"],
          "IND": ["indiana", "fever"], "ATL": ["atlanta", "dream"], "CHI": ["chicago", "sky"],
          "DAL": ["dallas", "wings"], "LV": ["las vegas", "aces"], "MIN": ["minnesota", "lynx"],
          "PHX": ["phoenix", "mercury"], "LA": ["los angeles", "sparks"], "POR": ["portland", "fire"]}


def get(url, tries=2):
    for i in range(tries):
        try:
            r = creq.get(url, impersonate="chrome", headers={"User-Agent": UA}, timeout=25)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return r.json()
            print("  HTTP", r.status_code)
        except Exception as e:
            print("  err", str(e)[:50])
        time.sleep(3)
    return None


def gz(g):
    return (f"{BASE}/LineFeed/GetGameZip?id={g}&lng=en&country=115&mode=4&grMode=4"
            "&GroupEvents=true&isSubGames=true&countevents=500&marketType=1")


def espn_near(window):
    """FREE pre-gate: ESPN games within `window` min of tip (and not past). -> [(away,home)]"""
    out, now = [], datetime.datetime.now(datetime.timezone.utc)
    for d in (now.strftime("%Y%m%d"), (now + datetime.timedelta(days=1)).strftime("%Y%m%d")):
        try:
            j = json.load(urllib.request.urlopen(urllib.request.Request(ESPN + "?dates=" + d, headers={"User-Agent": UA}), timeout=20))
        except Exception:
            continue
        for ev in j.get("events", []):
            if (ev.get("status") or {}).get("type", {}).get("completed"):
                continue
            tip = ev.get("date", "")
            if not tip:
                continue
            mins = (datetime.datetime.fromisoformat(tip.replace("Z", "+00:00")) - now).total_seconds() / 60
            if 0 < mins <= window:
                cs = (ev.get("competitions") or [{}])[0].get("competitors", [])
                a = next((x for x in cs if x.get("homeAway") == "away"), {})
                h = next((x for x in cs if x.get("homeAway") == "home"), {})
                out.append(((a.get("team") or {}).get("abbreviation"), (h.get("team") or {}).get("abbreviation")))
    return out


def load_picks():
    picks = defaultdict(list)
    if not os.path.exists(PICKS):
        return picks
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    for r in csv.DictReader(open(PICKS, encoding="utf-8")):
        if r.get("pick_date") != today:
            continue
        base = r["market"].split("_")[0]
        side = "Over" if r["market"].endswith("over") else "Under"
        if base not in STAT_T or "disrupt" in r.get("signals", "").lower():
            continue
        if side == "Over" and base != "pra":
            continue
        picks[r["player"]].append({"base": base, "side": side, "anchor": float(r["anchor"]),
                                   "proj": float(r["proj"]), "fair": float(r["fair_odds"])})
    return picks


def ping(msg):
    print(msg)
    if not WEBHOOK:
        return
    try:
        urllib.request.urlopen(urllib.request.Request(WEBHOOK, data=json.dumps({"content": msg[:1900]}).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": UA}), timeout=15)
        print("discord: pinged")
    except Exception as e:
        print("discord:", e)


def proj_msg():
    picks = load_picks()
    if not picks:
        return "_(no model picks logged today)_"
    out = []
    for player, pks in picks.items():
        pk = sorted(pks, key=lambda x: {"pra": 0, "pr": 1, "pa": 2, "pts": 3, "ra": 4}.get(x["base"], 9))[0]
        zone = f"line≥{pk['anchor']-1:.1f}" if pk["side"] == "Under" else f"line≤{pk['anchor']+1:.1f}"
        out.append(f"• {player} {pk['base'].upper()} {pk['side']} — bet if 1xbet {zone} & odds>{pk['fair']} (proj {pk['proj']:.1f})")
    return "\n".join(out)


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    near = espn_near(WINDOW)
    if not near:
        print(f"ESPN pre-gate: no game within {WINDOW} min of tip; 0 calls to 1xbet."); return
    print(f"{len(near)} game(s) near tip -> probing 1xbet")
    nearkw = [TEAMKW.get(t, [t.lower()]) for ab in near for t in ab if t]

    disc = get(f"{BASE}/LineFeed/Get1x2_VZip?sports=3&champs={CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
    if not disc:                                    # Cloudflare blocked us -> projections fallback
        ping(f"⚠️ **1xbet scrape BLOCKED (Cloudflare) — {now.strftime('%H:%M')} UTC**\nCheck these on 1xbet yourself:\n" + proj_msg())
        return

    games = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
    target = [e for e in games if any(all(w in f"{e.get('O1','')} {e.get('O2','')}".lower() for w in kw) for kw in nearkw)]
    props = {}
    for e in target:
        mv = get(gz(e["I"]))
        sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
        stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
        if not stat:
            continue
        val = (get(gz(stat["I"])) or {}).get("Value", {}) or {}
        def walk(o):
            if isinstance(o, dict):
                pl = o.get("PL"); T = o.get("T")
                if isinstance(pl, dict) and T in T2S and o.get("P") is not None and o.get("C"):
                    st, sd = T2S[T]
                    props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((st, sd), []).append((float(o["P"]), float(o["C"])))
                for x in o.values(): walk(x)
            elif isinstance(o, list):
                for x in o: walk(x)
        walk(val)
    print(f"players on boards: {len(props)}")

    picks = load_picks()
    stamp = now.isoformat(timespec="seconds")
    rows, bets = [], []
    for player, pks in picks.items():
        pp = props.get(player.lower())
        if not pp:
            continue
        side = pks[0]["side"]; cands = []
        for pk in pks:
            outs = pp.get((pk["base"], pk["side"]))
            if not outs:
                continue
            line, odds = min(outs, key=lambda t: abs(t[0] - pk["anchor"]))
            rows.append([stamp, player, pk["base"], side, line, odds])
            zone = (line >= pk["anchor"] - 1) if side == "Under" else (line <= pk["anchor"] + 1)
            strong = (line >= pk["anchor"]) if side == "Under" else (line <= pk["anchor"])
            if odds > pk["fair"] and zone:
                cands.append((1 if strong else 0, pk["base"], line, odds))
        if cands:
            best = max(cands, key=lambda c: c[0])
            bets.append(f"• **{player}** {best[1].upper()} {side} **{best[2]} @ {best[3]}** [{'STRONG' if best[0] else 'marginal'}]")
    if rows:
        new = not os.path.exists(SNAP)
        with open(SNAP, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["captured_utc", "player", "market", "side", "line", "odds"])
            w.writerows(rows)
        print(f"logged {len(rows)} xbet snapshot rows")
    if bets:
        ping(f"🏀 **1xbet (cloud) — {now.strftime('%H:%M')} UTC**\n" + "\n".join(bets))
    else:
        print("no +EV bet in zone (lines may not be posted yet) — no ping")


if __name__ == "__main__":
    main()
