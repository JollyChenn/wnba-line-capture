# ============================================================================
# cloud_xbet.py — CLOUD 1xbet capture via 1x-bet.com (laptop-off, no browser).
# ESPN pre-gate (only touch 1xbet near tip) + LINEUP GATE (drop OUT, hold Day-To-Day)
# + STAR-OUT CASCADE (top-usage star scratched -> rank-3-6 teammates' PRA over, with
# live lines). If Cloudflare blocks the scrape -> ping model projections to check by hand.
# ============================================================================
import os, sys, csv, json, time, math, re, datetime, urllib.request
from collections import defaultdict
from zoneinfo import ZoneInfo
from curl_cffi import requests as creq
import pandas as pd, numpy as np
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://1x-bet.com/service-api"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"
CHAMP = "2874802"
WINDOW = int(os.environ.get("XBET_WINDOW_MIN", "180"))
_SLATE_TZ = ZoneInfo("America/Los_Angeles")   # picks are filed under the US slate date (matches daily_picks)
PING_MAX = int(os.environ.get("XBET_PING_MAX_MIN", "40"))   # only PING within this many min of tip (the ~30-min-before alert); capture still runs every cycle
NEAR_TIP_MIN = int(os.environ.get("XBET_NEARTIP_MIN", "90"))  # reconfirm window: within this many min of tip, surface day-to-day players + re-show injury/odds
PICKS, SNAP = "picks_log.csv", "xbet_snapshots.csv"
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
STAT_T = {"pts": (1807, 1806), "pr": (5671, 5672), "pa": (5673, 5674),
          "ra": (7141, 7142), "pra": (16427, 16428)}
T2S = {}
for _s, (_o, _u) in STAT_T.items():
    T2S[_o] = (_s, "Over"); T2S[_u] = (_s, "Under")
SCRATCH = {"out", "doubtful"}
HOLD = {"day-to-day", "questionable", "game-time decision"}
CASC_FAIR = 1.75
TEAMKW = {"SEA": ["seattle", "storm"], "GS": ["golden state", "valkyr"], "TOR": ["toronto", "tempo"],
          "WSH": ["washington", "mystic"], "NY": ["new york", "liberty"], "CON": ["connecticut", "sun"],
          "IND": ["indiana", "fever"], "ATL": ["atlanta", "dream"], "CHI": ["chicago", "sky"],
          "DAL": ["dallas", "wings"], "LV": ["las vegas", "aces"], "MIN": ["minnesota", "lynx"],
          "PHX": ["phoenix", "mercury"], "LA": ["los angeles", "sparks"], "POR": ["portland", "fire"]}


def _ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pkey(name):
    p = re.sub(r"[^a-z .'-]", "", name.lower()).replace(".", " ").split()
    return (p[0][0] + " " + p[-1]) if len(p) >= 2 else name.lower()


def _team_ab(name):
    n = (name or "").lower()
    for ab, kws in TEAMKW.items():
        if any(w in n for w in kws):
            return ab
    return (name or "")[:3].upper()


def pinnacle_lines():
    """Pinnacle WNBA single-stat prop lines (the sharp ~close) -> {player_key:{stat:line}}. Best-effort, for the CLV ref."""
    PB = "https://guest.api.arcadia.pinnacle.com/0.1"
    HK = {"X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R", "User-Agent": UA}
    SMAP = {"Points": "pts", "Rebounds": "reb", "Assists": "ast"}
    out = defaultdict(dict)
    try:
        mm = creq.get(PB + "/sports/4/matchups", impersonate="chrome", timeout=20, headers=HK).json()
        mk = creq.get(PB + "/sports/4/markets/straight", impersonate="chrome", timeout=20, headers=HK).json()
        mkt = {x["matchupId"]: x for x in mk if x.get("type") == "total" and x.get("prices")}
        for m in mm:
            if "wnba" not in json.dumps(m.get("league", {})).lower():
                continue
            mt = re.match(r"(.+?) Total (Points|Rebounds|Assists)\b", (m.get("special") or {}).get("description", ""))
            if mt and m["id"] in mkt:
                out[_pkey(mt.group(1))][SMAP[mt.group(2)]] = mkt[m["id"]]["prices"][0].get("points")
    except Exception as e:
        print("pinnacle ref unavailable:", str(e)[:40])
    return out


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
                out.append(((a.get("team") or {}).get("abbreviation"), (h.get("team") or {}).get("abbreviation"), mins))
    return out


def injuries():
    out = {}
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(INJ, headers={"User-Agent": UA}), timeout=20))
    except Exception:
        return out
    for tm in d.get("injuries", []):
        for it in tm.get("injuries", []):
            a = (it.get("athlete") or {}).get("displayName")
            if a:
                out[a.lower()] = (it.get("status") or "").lower()
    return out


def status_of(player, inj):
    s = inj.get(player.lower(), "")
    if not s:                                  # first-initial + surname (avoid surname-only collisions, e.g. two "Jones")
        p = player.lower().split()
        key = (p[0][0] + " " + p[-1]) if len(p) >= 2 else player.lower()
        for k, v in inj.items():
            kp = k.split()
            if len(kp) >= 2 and kp[0][0] + " " + kp[-1] == key:
                s = v; break
    return "OUT" if s in SCRATCH else "HOLD" if s in HOLD else "OK"


def watchlist(teams):
    """Per team in `teams`: top-usage star (>=24 min) + rank-3-6 PRA-beneficiaries, from box_2026.csv."""
    if not (os.path.exists("data/box_2026.csv") and os.path.exists("data/games_2026.csv")):
        return {}
    try:
        box = pd.read_csv("data/box_2026.csv", dtype={"game_id": str})
        g = pd.read_csv("data/games_2026.csv", dtype={"game_id": str})
        box = box.join(g.set_index("game_id")[["date"]], on="game_id")
        for c in ["pts", "reb", "ast", "fga", "fta", "to", "min"]:
            box[c] = pd.to_numeric(box[c], errors="coerce")
        box["pra"] = box.pts + box.reb + box.ast
        box["usg"] = box.fga + 0.44 * box.fta + box.to
        box["dt"] = pd.to_datetime(box.date.astype(str), format="%Y%m%d", errors="coerce")
        box = box.sort_values(["aid", "dt"])
    except Exception as e:
        print("watchlist load err", e); return {}
    feats = []
    for (aid, team), grp in box.groupby(["aid", "team"]):
        if len(grp) < 5:
            continue
        feats.append({"player": grp.player.iloc[-1], "team": team, "usg": grp.usg.tail(5).mean(),
                      "med_pra": grp.pra.tail(10).median(), "mins": grp["min"].tail(5).mean()})
    f = pd.DataFrame(feats)
    wl = {}
    for team, tt in f.groupby("team"):
        if team not in teams:
            continue
        tt = tt.sort_values("usg", ascending=False)
        if len(tt) < 5 or tt.iloc[0].mins < 24:
            continue
        wl[team] = {"star": tt.iloc[0].player,
                    "ben": [(b.player, float(b.med_pra)) for _, b in tt.iloc[2:6].iterrows()]}
    return wl


def load_picks():
    picks = defaultdict(list)
    if not os.path.exists(PICKS):
        return picks
    today = datetime.datetime.now(_SLATE_TZ).date().isoformat()    # LA slate date, NOT UTC (else late West-coast games go blind 00:00-07:00 UTC)
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
                                   "proj": float(r["proj"]), "fair": float(r["fair_odds"]),
                                   "sd": float(r.get("sd") or 0),
                                   "team": r.get("team", ""), "sig": r.get("signals", "")})
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


def proj_msg(inj=None):
    picks = load_picks()
    if not picks:
        return "_(no model picks logged today)_"
    out, benched = [], []
    for player, pks in picks.items():
        st = status_of(player, inj) if inj else "OK"
        if st == "OUT":
            benched.append(player); continue                        # never suggest an OUT player
        pk = sorted(pks, key=lambda x: {"pra": 0, "pr": 1, "pa": 2, "pts": 3, "ra": 4}.get(x["base"], 9))[0]
        zone = f"line≥{pk['anchor']-1:.1f}" if pk["side"] == "Under" else f"line≤{pk['anchor']+1:.1f}"
        flag = " ⏳unconfirmed-injury" if st == "HOLD" else ""
        out.append(f"• {player} {pk['base'].upper()} {pk['side']} — bet if 1xbet {zone} & odds>{pk['fair']} (proj {pk['proj']:.1f}){flag}")
    msg = "\n".join(out) if out else "_(all candidates are OUT)_"
    if benched:
        msg += "\n❌ OUT (skip): " + ", ".join(benched)
    return msg


def pra_line(props, player):
    """A player's live 1xbet PRA over (line, odds) if posted."""
    pp = props.get(player.lower())
    if not pp:
        return None
    outs = pp.get(("pra", "Over"))
    return min(outs, key=lambda t: t[0]) if outs else None


def overshoot_overs(props, inj, picked):
    """Board-wide deep overshoot-overs: ANY player (not just our signal-picks) whose 1xbet over line
       sits >=3 below their trailing median. The soft book is lagging -> +EV over. Injury-gated; flagged
       to verify no role/injury news (a line that low can also mean the book knows something)."""
    import statistics
    if not os.path.exists("data/box_2026.csv") or not os.path.exists("data/games_2026.csv"):
        return []
    gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
    log = defaultdict(list)
    for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
        try:
            log[r["player"].lower()].append((gd.get(r["game_id"]), float(r["pts"]), float(r["reb"]), float(r["ast"])))
        except (ValueError, TypeError):
            pass
    pick = {"pts": lambda x: x[1], "pr": lambda x: x[1] + x[2], "pa": lambda x: x[1] + x[3], "pra": lambda x: x[1] + x[2] + x[3]}
    out = []
    for plow, mk in props.items():
        for (st, sd), outs in mk.items():
            if sd != "Over" or st not in pick or (plow, st) in picked:
                continue
            line, odds = min(outs, key=lambda t: t[0])
            g = sorted([x for x in log.get(plow, []) if x[0]], key=lambda t: t[0])
            v = [pick[st](x) for x in g]
            if len(v) < 5:
                continue
            v10 = v[-10:]; med = statistics.median(v10); t3 = statistics.mean(v[-3:])
            if line > med - 3 or t3 <= med - 3:              # DEEP overshoot only; skip COLD form (book is likely pricing a real decline = trap)
                continue
            proj = med + 0.25 * (t3 - med)                   # calibrated proj from the backtest
            hit = 1 - _ncdf((line - proj) / (statistics.pstdev(v10) or 1)); ev = odds * hit - 1
            name = plow.title(); stt = status_of(name, inj)
            if ev > 0 and stt != "OUT":                      # OUT auto-dropped; day-to-day kept but flagged
                out.append((hit, name, st, line, odds, ev, med, stt))
    return sorted(out, reverse=True)[:6]


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    near = espn_near(WINDOW)
    if not near:
        print(f"ESPN pre-gate: no game within {WINDOW} min of tip; 0 calls to 1xbet."); return
    teams = set(t for a, h, _ in near for t in (a, h) if t)
    print(f"{len(near)} game(s) near tip -> probing 1xbet")
    nearkw = [TEAMKW.get(t, [t.lower()]) for t in teams]
    inj = injuries()                                  # ESPN injury report (works even when 1xbet is blocked)

    disc = get(f"{BASE}/LineFeed/Get1x2_VZip?sports=3&champs={CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
    if not disc:
        ping(f"⚠️ **1xbet scrape BLOCKED (Cloudflare) — {now.strftime('%H:%M')} UTC**\nCheck these on 1xbet yourself:\n" + proj_msg(inj))
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
    pin = pinnacle_lines()   # sharp reference lines, shown next to each bet for live CLV

    picks = load_picks()
    stamp = now.isoformat(timespec="seconds")
    rows, bets, holds, drops, betstruct = [], [], [], [], []
    def _tier(p):                                     # honest strength = the model's hit probability at the line
        return "STRONG" if p >= 0.66 else "SOLID" if p >= 0.58 else "THIN"

    for player, pks in picks.items():
        pp = props.get(player.lower())
        if not pp:
            continue
        st = status_of(player, inj)
        if st == "OUT":
            drops.append(player); continue
        side = pks[0]["side"]; cands = []
        for pk in pks:
            # ---- the model's own side (an under, or a PRA over) ----
            outs = pp.get((pk["base"], pk["side"]))
            if outs:
                line, odds = min(outs, key=lambda t: abs(t[0] - pk["anchor"]))
                rows.append([stamp, player, pk["base"], pk["side"], line, odds])
                zone = (line >= pk["anchor"] - 1) if side == "Under" else (line <= pk["anchor"] + 1)
                if pk.get("sd"):
                    # de-inflate the hot-over projection (backtest: actual regresses ~15% toward the median)
                    proj = pk["proj"] if side == "Under" else pk["anchor"] + 0.85 * (pk["proj"] - pk["anchor"])
                    ph = _ncdf((line - proj) / pk["sd"]); ph = ph if side == "Under" else 1 - ph
                    fairL = 1 / max(ph, 0.02)
                else:
                    ph, fairL = 1 / pk["fair"], pk["fair"]
                if odds > fairL and zone:
                    cands.append((ph, pk["base"], side, line, odds, odds / fairL - 1))
            # ---- overshoot FLIP: under-signal player whose 1xbet OVER line overshot below our projection ----
            if side == "Under" and pk.get("sd"):
                oo = pp.get((pk["base"], "Over"))
                if oo:
                    oline, oodds = min(oo, key=lambda t: t[0])               # most-overshot (lowest) over line
                    if oline <= pk["anchor"] - 2 and oline < pk["proj"]:      # genuine overshoot, below our proj
                        pov = 1 - _ncdf((oline - pk["proj"]) / pk["sd"]); ofair = 1 / max(pov, 0.02)
                        if oodds > ofair:
                            rows.append([stamp, player, pk["base"], "Over", oline, oodds])
                            cands.append((pov, pk["base"], "Over", oline, oodds, oodds / ofair - 1))
        if cands:
            ph, base, bside, line, odds, ev = max(cands, key=lambda c: c[0])  # highest-confidence bet for this player
            if st == "OK":                            # log confirmed-active model bets for grading (+ Pinnacle line for sharp CLV)
                betstruct.append([player, base, bside, line, odds, _tier(ph), round(ev, 3), pin.get(_pkey(player), {}).get(base, "")])
            pinref = pin.get(_pkey(player), {}).get(base)
            cstr = f" · Pinn {pinref}" if pinref is not None else ""
            tmab = _team_ab(pks[0].get("team", "")); sig = pks[0].get("sig", "")
            flip = " 🎯FLIP" if (bside == "Over" and side == "Under") else ""
            txt = f"• **{player}** ({tmab}) {base.upper()} {bside} **{line} @ {odds}** [{_tier(ph)}{flip} · {sig} · hit {ph*100:.0f}% · EV {ev*100:+.0f}%]{cstr}"
            (holds if st == "HOLD" else bets).append(txt + (" ⏳unconfirmed" if st == "HOLD" else ""))

    # ---- STAR-OUT CASCADE ----
    casc = []
    for team, w in watchlist(teams).items():
        if status_of(w["star"], inj) != "OUT":
            continue
        legs = []
        for ben, med in w["ben"]:
            if status_of(ben, inj) == "OUT":          # a beneficiary who is also out can't carry the cascade
                continue
            live = pra_line(props, ben)
            if live and live[0] <= med + 1 and live[1] > CASC_FAIR:        # value zone + beats cascade-fair
                legs.append(f"{ben} O{live[0]}@{live[1]}")
            else:
                legs.append(f"{ben} O{np.floor(med-0.001)+0.5:.1f} PRA (1xbet? need >{CASC_FAIR})")
        casc.append(f"🚨 **{team}: {w['star']} OUT** → cascade PRA OVER: " + ", ".join(legs))

    # ---- board-wide overshoot-overs (any player whose 1xbet over line is >=3 below their median) ----
    picked = {(p.lower(), pk["base"]) for p, pks in picks.items() for pk in pks}
    osc = overshoot_overs(props, inj, picked)
    for h, n, st, ln, od, ev, med, stt in osc:
        rows.append([stamp, n, st, "Over", ln, od])     # capture ALL overshoots for CLV (display filtered below)

    if rows:
        new = not os.path.exists(SNAP)
        with open(SNAP, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["captured_utc", "player", "market", "side", "line", "odds"])
            w.writerows(rows)
        print(f"logged {len(rows)} xbet snapshot rows")

    min_mins = min(t[2] for t in near)
    near_tip = min_mins <= NEAR_TIP_MIN              # reconfirm window: only this close to tip do we surface day-to-day players
    # injury-confidence: vague (day-to-day) overshoots stay hidden until the near-tip reconfirm
    osc_show = [x for x in osc if near_tip or x[7] == "OK"]
    for h, n, st, ln, od, ev, med, stt in osc_show:
        if stt == "OK":                              # log confirmed-active overshoot bets for grading (+ Pinnacle line for sharp CLV)
            betstruct.append([n, st, "Over", ln, od, _tier(h), round(ev, 3), pin.get(_pkey(n), {}).get(st, "")])
    oso = [f"• **{n}** {st.upper()} Over **{ln} @ {od}** [🎯 hit {h*100:.0f}% · EV {ev*100:+.0f}% · med {med:.0f} · {'✓ active' if stt == 'OK' else '⏳ DAY-TO-DAY'}]"
           for h, n, st, ln, od, ev, med, stt in osc_show]
    holds_show = holds if near_tip else []           # day-to-day model bets: hold them back until near tip
    if bets or casc or oso:                          # GOOD line(s) found -> ping now (every-3h "ping if good" + near-tip "once more")
        if betstruct:                                # log the actual bets so grade_bets.py can settle them after games
            la_today = datetime.datetime.now(_SLATE_TZ).date().isoformat()
            bnew = not os.path.exists("bets_log.csv")
            with open("bets_log.csv", "a", newline="", encoding="utf-8") as bf:
                wbl = csv.writer(bf)
                if bnew:
                    wbl.writerow(["captured_utc", "date", "player", "market", "side", "line", "odds", "tier", "ev", "pinn"])
                for b in betstruct:
                    wbl.writerow([stamp, la_today] + b)
        parts = []
        if near_tip:
            parts.append(f"🔔 **NEAR TIP (~{int(min_mins)} min) — injury list & odds RECONFIRMED**")
        if bets:
            parts.append("✅ **BETS** (our model · line@odds · Pinn = sharp close for CLV):\n" + "\n".join(bets))
        if oso:
            parts.append("🎯 **OVERSHOOT-OVERS** (book line ≥3 below median; ✓ active = injury auto-checked, just eyeball rotation):\n" + "\n".join(oso))
        if casc:
            parts.append("🧪 **EXPERIMENTAL** (star-out cascade — ~57% unproven, size small):\n" + "\n".join(casc))
        if holds_show:
            parts.append("⏳ HOLD (still unconfirmed at tip): " + ", ".join(h.split("**")[1] for h in holds_show))
        if drops:
            parts.append("❌ OUT (injury → dropped): " + ", ".join(drops))
        ping(f"🏀 **1xbet — ~{int(min_mins)} min to tip**\n" + "\n".join(parts))
    elif min_mins <= PING_MAX:                        # near tip + no +EV line -> fallback (don't go dark)
        ping(f"⏰ **1xbet — tip in ~{int(min_mins)} min, no +EV line found**\n"
             "(props may be unposted, or the posted price isn't in value). Model picks to check on 1xbet by hand:\n"
             + proj_msg(inj))
    else:
        print(f"captured {len(rows)} rows for CLV; nearest tip {int(min_mins)} min — no +EV line yet")


if __name__ == "__main__":
    main()
