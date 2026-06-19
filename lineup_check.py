# lineup_check.py — NEAR-TIP LINEUP GUARD (the before-tip official-lineup confirmation).
# Cross-confirms every PICK player across THREE sources and pings BEFORE tip so you never
# accidentally bet a scratch or a shaky day-to-day:
#   1) ESPN injuries feed  ............ out/doubtful + day-to-day (hours ahead)
#   2) ESPN summary boxscore.players .. the OFFICIAL confirmed actives (~T-30)
#   3) RotoWire lineups (fail-open) ... projected/confirmed + play-% (earliest, non-ESPN)
# Three tiers: ❌ PULL  (confirmed OUT / not in the confirmed lineup)
#             ⚠️ DO NOT BET (day-to-day / GTD / doubtful — uncertain, don't risk it)
#             📈 LINE MOVED (>=2 against our thesis since first capture = sharp market correcting us -> skip)
# Idempotent via lineup_pinged.json. stdlib-only. Runs every ~10 min in tip hours.
import os, sys, json, re, csv, datetime, urllib.request, unicodedata
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
SUM = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/summary?event="
INJ = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"
ROTO = "https://www.rotowire.com/wnba/lineups.php"
STATE = "lineup_pinged.json"
TIPW = int(os.environ.get("LINEUP_WINDOW_MIN", "90"))     # start confirming this many min before tip
SCR_INJ = {"out", "doubtful"}                             # hard scratch
FLAG_WORDS = ("day-to-day", "day to day", "quest", "game-time", "game time", "probable", "gtd")
PAPER_SIGS = {"ftdrought", "steady", "usgshock"}


def key_of(n):                                        # robust FULL-name key — no same-initial/last-name collision (Chance vs Chelsea Gray); folds accents
    s = unicodedata.normalize("NFKD", str(n or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip() or str(n or "").lower()


def getj(u):
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20))
    except Exception:
        return {}


def gethtml(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "replace")


def ping(msg):
    if not WEBHOOK:
        print("[no webhook]\n" + msg); return
    try:
        urllib.request.urlopen(urllib.request.Request(
            WEBHOOK, data=json.dumps({"content": msg}).encode(),
            headers={**UA, "Content-Type": "application/json"}), timeout=15)
        print("pinged Discord")
    except Exception as e:
        print("discord err", e)


# --- source 1: ESPN injuries -------------------------------------------------
inj = {}
for tm in getj(INJ).get("injuries", []):
    for it in tm.get("injuries", []):
        a = (it.get("athlete") or {}).get("displayName")
        if a:
            inj[key_of(a)] = (it.get("status") or "").lower()

# --- source 3: RotoWire projected/confirmed (fail-open) ----------------------
# Each player li: class="lineup__player is-pct-play-100" title="STATUS" ... <a title="NAME" href="/wnba/player/
def rotowire():
    rw = {}
    try:
        html = gethtml(ROTO)
    except Exception as e:
        print("rotowire fetch failed (fail-open):", e); return rw
    for m in re.finditer(
            r'lineup__player\b[^>]*?is-pct-play-(\d+)"[^>]*?title="([^"]*)"[^>]*>.*?<a title="([^"]+)" href="/wnba/player/',
            html, re.S):
        pct = int(m.group(1)); status = m.group(2).strip(); k = key_of(m.group(3))
        if k not in rw or pct < rw[k][0]:                 # keep the worst (lowest play-%)
            rw[k] = (pct, status)
    return rw

rw = rotowire()

# --- pick players (latest slate) + tip times ---------------------------------
if not os.path.exists("picks_log.csv"):
    print("no picks_log.csv"); raise SystemExit
rows = [r for r in csv.DictReader(open("picks_log.csv", encoding="utf-8"))]
if not rows:
    print("picks_log empty"); raise SystemExit
latest = max(r["pick_date"] for r in rows)
picks = {}
for r in rows:
    if r["pick_date"] != latest:
        continue
    k = key_of(r["player"]); real = r.get("signals", "") not in PAPER_SIGS
    prev = picks.get(k)
    picks[k] = (r["player"], r["game_id"], r.get("team", ""), (prev[3] if prev else False) or real)

# --- LINE-MOVE CHECK (the "two lines" case, e.g. Hamby PRA 22.5 -> 25.5) -------
# bets_log already stores EVERY snapshot (both the open line and the moved line). Near tip we compare the
# OPEN line (first capture today) to the CURRENT line (last) per REAL-money bet. A move >= LINE_TOL AGAINST
# our thesis (UNDER line RISES, or OVER line DROPS) = the sharp market is correcting our stale signal -> skip.
# (A line moving WITH us — under line drops / over line rises — is the market agreeing; not flagged.)
LINE_TOL = float(os.environ.get("LINE_MOVE_TOL", "2.0"))
linemoves = {}                                            # key_of(player) -> ["MKT SIDE opened X -> now Y (+Δ against)"]
if os.path.exists("bets_log.csv"):
    blog = [r for r in csv.DictReader(open("bets_log.csv", encoding="utf-8")) if r.get("player")]
    bdate = max((r.get("date", "") for r in blog), default="")
    caps = {}                                             # (pkey, market, side) -> [(captured_utc, line)]
    for r in blog:
        if r.get("date") != bdate or (r.get("src") or "") != "model":   # today's REAL-money captures only
            continue
        try: ln = float(r["line"])
        except (ValueError, KeyError): continue
        caps.setdefault((key_of(r["player"]), r["market"], r["side"]), []).append((r.get("captured_utc", ""), ln))
    for (pk, mkt, side), lst in caps.items():
        lst.sort(); ol, cur = lst[0][1], lst[-1][1]
        against = round((cur - ol) if side == "Under" else (ol - cur), 1)   # >0 = moved AGAINST our thesis
        if against >= LINE_TOL:
            linemoves.setdefault(pk, []).append(f"{mkt.upper()} {side} opened {ol}→now {cur} ({against:+.1f} against)")

tips = {}
if os.path.exists("data/games_2026.csv"):
    for g in csv.DictReader(open("data/games_2026.csv", encoding="utf-8")):
        t = g.get("tip", "")
        if t:
            try: tips[str(g["game_id"])] = datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception: pass
now = datetime.datetime.now(datetime.timezone.utc)
def mins_to_tip(gid):
    tp = tips.get(str(gid))
    return (tp - now).total_seconds() / 60 if tp else None

# --- source 2: ESPN confirmed actives (cached) -------------------------------
_acts = {}
def actives(gid):
    if gid in _acts:
        return _acts[gid]
    s = set()
    for tm in getj(SUM + str(gid)).get("boxscore", {}).get("players", []):
        for st in tm.get("statistics", []):
            for a in st.get("athletes", []):
                nm = (a.get("athlete") or {}).get("displayName")
                if nm: s.add(key_of(nm))
    _acts[gid] = (s, len(s) > 0)
    return _acts[gid]

# --- classify each pick player (only games approaching tip) ------------------
pull, flag, linmv = [], [], []   # (name, team, is_real, mins, reasons) — linmv = line moved >=2 against our thesis
for k, (name, gid, team, real) in picks.items():
    m = mins_to_tip(gid)
    if m is None or m > TIPW or m < -15:
        continue
    scr_r, flg_r = [], []
    ei = inj.get(k, "")
    if ei in SCR_INJ:
        scr_r.append(f"ESPN {ei}")
    elif ei and any(w in ei for w in FLAG_WORDS):
        flg_r.append(f"ESPN {ei}")
    if k in rw:
        pct, stxt = rw[k]
        if pct == 0: scr_r.append(f"RotoWire {stxt}")
        elif pct < 100: flg_r.append(f"RotoWire {stxt} {pct}%")
    acts, posted = actives(gid)
    if posted and k not in acts:
        scr_r.append("NOT in confirmed lineup")
    if scr_r:
        pull.append((name, team, real, m, scr_r))
    elif flg_r:
        flag.append((name, team, real, m, flg_r))
    if not scr_r and linemoves.get(k):                # line moved >=2 against our side (and not already a scratch)
        linmv.append((name, team, real, m, linemoves[k]))

# --- dedup + ping (separate tiers so flag->scratch escalation re-pings) -------
state = set(json.load(open(STATE))) if os.path.exists(STATE) else set()
def fresh(items, tier):
    out = []
    for it in items:
        key = f"{latest}|{key_of(it[0])}|{tier}"
        if key not in state:
            out.append(it); state.add(key)
    return out

new_pull, new_flag, new_mv = fresh(pull, "scr"), fresh(flag, "flag"), fresh(linmv, "lin")
if new_pull or new_flag or new_mv:
    def line(it):
        name, team, real, m, rs = it
        tag = "💰 " if real else "🧪 "
        return f"   {tag}**{name}** ({team}, ~{m:.0f} min) — {'; '.join(rs)}"
    parts = ["🚨 **NEAR-TIP GUARD — confirm before betting:**"]
    if new_pull:
        parts.append("❌ **PULL (confirmed out / not in lineup):**\n" + "\n".join(line(i) for i in new_pull))
    if new_flag:
        parts.append("⚠️ **DO NOT BET (day-to-day / uncertain):**\n" + "\n".join(line(i) for i in new_flag))
    if new_mv:
        parts.append("📈 **LINE MOVED ≥2 AGAINST — skip/shrink (sharp market correcting our signal):**\n" + "\n".join(line(i) for i in new_mv))
    ping("\n".join(parts))
    json.dump(sorted(state), open(STATE, "w"))
    print("pulls:", [i[0] for i in new_pull], "| flags:", [i[0] for i in new_flag], "| line-moves:", [i[0] for i in new_mv])
else:
    inwin = [k for k, (n, g, t, r) in picks.items()
             if (mins_to_tip(g) is not None and -15 <= mins_to_tip(g) <= TIPW)]
    nearest = min((mins_to_tip(picks[k][1]) for k in inwin), default=None)
    print(f"lineup guard: {len(inwin)} pick players within {TIPW} min "
          f"({'nearest ~%.0f min' % nearest if nearest is not None else 'none near tip'}), "
          f"no new flags · ESPN inj={len(inj)} RotoWire={len(rw)} · line-moves flagged={sum(len(v) for v in linemoves.values())} · slate {latest}")
