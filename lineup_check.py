# lineup_check.py — NEAR-TIP LINEUP GUARD (the ~20-min-before confirmed-lineup check).
# ESPN confirmed actives (boxscore.players) populate ~30 min pre-tip. This re-checks every
# PICK player against BOTH the injury feed AND the confirmed actives, and pings Discord the
# instant a player we'd bet becomes a LATE SCRATCH (out/doubtful, or lineup posted and they're
# not in it) -> pull the bet. Idempotent via lineup_pinged.json. stdlib-only (no pip).
# Run every ~15 min during tip hours (workflow: lineup-confirm.yml).
import os, sys, json, re, csv, datetime, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
H = {"User-Agent": "Mozilla/5.0"}        # Discord silently drops default-agent posts -> UA required
SUM = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"
STATE = "lineup_pinged.json"
SCRATCH = {"out", "doubtful"}
PAPER_SIGS = {"ftdrought", "steady", "usgshock"}   # everything else = real-money (model/flip/hot)


def key_of(n):
    p = re.sub(r"[^a-z .'-]", "", n.lower()).replace(".", " ").split()
    return (p[0][0] + " " + p[-1]) if len(p) >= 2 else n.lower()


def getj(u):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=20))
    except Exception:
        return {}


def ping(msg):
    if not WEBHOOK:
        print("[no webhook]\n" + msg); return
    try:
        urllib.request.urlopen(urllib.request.Request(
            WEBHOOK, data=json.dumps({"content": msg}).encode(),
            headers={**H, "Content-Type": "application/json"}), timeout=15)
        print("pinged Discord")
    except Exception as e:
        print("discord err", e)


# injury feed -> {key: status}
inj = {}
for tm in getj(INJ).get("injuries", []):
    for it in tm.get("injuries", []):
        a = (it.get("athlete") or {}).get("displayName")
        if a:
            inj[key_of(a)] = (it.get("status") or "").lower()

# pick players (latest slate), real-money flagged
if not os.path.exists("picks_log.csv"):
    print("no picks_log.csv"); raise SystemExit
rows = list(csv.DictReader(open("picks_log.csv", encoding="utf-8")))
if not rows:
    print("picks_log empty"); raise SystemExit
latest = max(r["pick_date"] for r in rows)
picks = {}
for r in rows:
    if r["pick_date"] != latest:
        continue
    k = key_of(r["player"])
    is_real = r.get("signals", "") not in PAPER_SIGS
    prev = picks.get(k)
    picks[k] = (r["player"], r["game_id"], (prev[2] if prev else False) or is_real)

# tip times (UTC) -> only run the official-lineup check as each game APPROACHES tip
TIPW = int(os.environ.get("LINEUP_WINDOW_MIN", "45"))   # start checking ~45 min out (ESPN posts actives ~T-30)
tips = {}
if os.path.exists("data/games_2026.csv"):
    for g in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
        t = g.get("tip", "")
        if t:
            try:
                tips[str(g["game_id"])] = datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception:
                pass
now = datetime.datetime.now(datetime.timezone.utc)
def mins_to_tip(gid):
    tp = tips.get(str(gid))
    return (tp - now).total_seconds() / 60 if tp else None

# confirmed actives per game (cached) — empty until ESPN posts the lineup (~30 min pre-tip)
_acts = {}
def actives(gid):
    if gid in _acts:
        return _acts[gid]
    s = set()
    for tm in getj(SUM + str(gid)).get("boxscore", {}).get("players", []):
        for st in tm.get("statistics", []):
            for a in st.get("athletes", []):
                nm = (a.get("athlete") or {}).get("displayName")
                if nm:
                    s.add(key_of(nm))
    _acts[gid] = (s, len(s) > 0)
    return _acts[gid]

# resolve scratches among our pick players — ONLY for games in the ~T-45..T-0 window
scratched = []
for k, (name, gid, is_real) in picks.items():
    m = mins_to_tip(gid)
    if m is None or m > TIPW or m < -15:          # too early (lineup not up) or game already underway -> skip
        continue
    tnote = f", ~{m:.0f} min to tip"
    st = inj.get(k, "")
    if st in SCRATCH:
        scratched.append((name, is_real, f"{st.upper()} (injury feed){tnote}")); continue
    acts, posted = actives(gid)
    if posted and k not in acts:
        scratched.append((name, is_real, f"NOT in confirmed lineup{tnote}"))

# dedup + ping (one alert per player per slate)
state = set(json.load(open(STATE))) if os.path.exists(STATE) else set()
new = [(n, real, why) for (n, real, why) in scratched if f"{latest}|{key_of(n)}" not in state]
if new:
    reals = [f"**{n}** — {why}" for n, real, why in new if real]
    paps  = [f"{n} — {why}" for n, real, why in new if not real]
    parts = ["🚨 **LINEUP GUARD — late scratch, pull these bets:**"]
    if reals: parts.append("✅ real-money: " + "; ".join(reals))
    if paps:  parts.append("🧪 paper: " + "; ".join(paps))
    ping("\n".join(parts))
    for n, _, _ in new:
        state.add(f"{latest}|{key_of(n)}")
    json.dump(sorted(state), open(STATE, "w"))
    print("scratches pinged:", [n for n, _, _ in new])
else:
    inwin = [(n, g) for k, (n, g, r) in picks.items()
             if (mins_to_tip(g) is not None and -15 <= mins_to_tip(g) <= TIPW)]
    nearest = min((mins_to_tip(g) for _, g in inwin), default=None)
    near_s = f"nearest tip ~{nearest:.0f} min" if nearest is not None else "no game within window"
    print(f"lineup guard: {len(inwin)} pick players within {TIPW} min of tip, no new scratches "
          f"({near_s}); slate {latest}")
