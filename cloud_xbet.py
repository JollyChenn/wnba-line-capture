# ============================================================================
# cloud_xbet.py — CLOUD 1xbet capture via 1x-bet.com (works from a GitHub datacenter
# IP; no browser). Discovers WNBA games, pulls near-tip prop boards, matches our
# picks to live lines (value zone + beats fair), logs xbet_snapshots.csv, pings Discord.
# Laptop-OFF — this is the school-proof half.
# ============================================================================
import os, sys, csv, json, datetime
from collections import defaultdict
from curl_cffi import requests as creq
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://1x-bet.com/service-api"
CHAMP = "2874802"
WINDOW = int(os.environ.get("XBET_WINDOW_MIN", "180"))      # capture games tipping within N min
PICKS, SNAP = "picks_log.csv", "xbet_snapshots.csv"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
STAT_T = {"pts": (1807, 1806), "pr": (5671, 5672), "pa": (5673, 5674),
          "ra": (7141, 7142), "pra": (16427, 16428)}
T2S = {}
for _s, (_o, _u) in STAT_T.items():
    T2S[_o] = (_s, "Over"); T2S[_u] = (_s, "Under")


def get(url):
    try:
        r = creq.get(url, impersonate="chrome", headers={"User-Agent": UA}, timeout=25)
        if r.status_code == 200 and r.text.strip().startswith("{"):
            return r.json()
        print("  HTTP", r.status_code)
    except Exception as e:
        print("  get err", str(e)[:60])
    return None


def gz(g):
    return (f"{BASE}/LineFeed/GetGameZip?id={g}&lng=en&country=115&mode=4&grMode=4"
            "&GroupEvents=true&isSubGames=true&countevents=500&marketType=1")


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


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    disc = get(f"{BASE}/LineFeed/Get1x2_VZip?sports=3&champs={CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
    games = [e for e in (disc.get("Value", []) if disc else []) if isinstance(e, dict) and e.get("O1") and e.get("I") and e.get("S")]
    print(f"WNBA games discovered: {len(games)}")
    near = [e for e in games if 0 < (e["S"] - now.timestamp()) / 60 <= WINDOW]
    if not near:
        print(f"no game within {WINDOW} min of tip; 0 captures."); return
    props = {}
    for e in near:
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
    msg = f"🏀 **1xbet (cloud) — {now.strftime('%H:%M')} UTC**\n" + ("\n".join(bets) if bets else "_no +EV bet in zone_")
    print(msg)
    if bets and WEBHOOK:
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(WEBHOOK, data=json.dumps({"content": msg}).encode(),
                                   headers={"Content-Type": "application/json", "User-Agent": UA}), timeout=15)
            print("discord: pinged")
        except Exception as e:
            print("discord:", e)


if __name__ == "__main__":
    main()
