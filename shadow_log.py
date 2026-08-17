# shadow_log.py - log what EVERY rejected filter would have bet tonight, so that in six weeks
# we have a real forward comparison instead of an argument about a backtest.
# ---------------------------------------------------------------------------------------------
# WHY THIS EXISTS. Over the last four nights the drift gate showed 3-0, +81% ROI, and the live
# model showed 5-4, -1.2%. On the full sample the drift gate is worth nothing (+8.3% vs +8.7%
# for no filter at all) - it just happened to be holding no ticket on the one bad night. Four
# nights cannot choose between configurations, and neither can forty bets. The only way to
# settle it is to log every candidate rule at DECISION TIME and let them run side by side.
#
# Decision time matters. Reconstructing later from xbet_board would use the final board state,
# which is not what we could have acted on. This records the line and price visible right now.
#
# SILENT BY DESIGN. It never pings. Only model_card.py (tonight's card) and ping_results.py
# (last night's result) are allowed to notify.
import csv, os, sys, datetime, collections, statistics
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.datetime.now(datetime.timezone.utc)
WINDOW_H = float(sys.argv[1]) if len(sys.argv) > 1 else 16.0
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
BET_MKTS = ("pra", "pr", "pts")
SIGS = ("flip", "hotover", "overshoot")
OUT = os.path.join(D, "shadow_forward.csv")
COLS = ["slate", "config", "player", "market", "line", "odds", "src",
        "prev_line", "mv", "drift", "tip", "logged_utc", "result", "actual"]

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

# ---- tonight ---------------------------------------------------------------------------------
tips = {}
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t and 0 < (t-NOW).total_seconds() < WINDOW_H*3600:
        tips[g["home"]] = t; tips[g["away"]] = t
if not tips:
    print("  shadow: no tips in window"); raise SystemExit
slate = min(tips.values()).strftime("%Y-%m-%d")
first_tip = min(tips.values())

# ---- board, anchored to GAMES (same fix as model_card.py 2026-08-15) --------------------------
# The old version bucketed by "started within 30h of tip". 1xbet posts lines a median 29.9h out,
# so half of all live lines were landing in the previous-game bucket. Shadow rows must be built
# from exactly the same view as the card or the comparison is meaningless.
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))

teamnow = {}
gm = {g.get("game_id"): g.get("date","") for g in load("data/games_2026.csv")}
for r in load("data/box_2026.csv"):
    if gm.get(r.get("game_id")): teamnow[(r.get("player") or "").lower()] = r.get("team")

tips_of = collections.defaultdict(list)
for g in load("data/games_2026.csv"):
    t = ts(g.get("tip"))
    if t:
        tips_of[g["home"]].append(t); tips_of[g["away"]].append(t)
for v in tips_of.values(): v.sort()

def game_for(team, when):
    for t in tips_of.get(team, []):
        if when <= t and (t - when).total_seconds() <= 60*3600:
            return t
    return None

bygame = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    tm = teamnow.get(pl)
    if tm is None: continue
    for t, o in sorted(v):
        gt = game_for(tm, t)
        if gt is None: continue
        bygame[(pl, mk, gt)].append((t, ln, o))
for v in bygame.values(): v.sort()

# ---- candidates, exactly as model_card builds them --------------------------------------------
seen, C = set(), []
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    bd = (b.get("date") or "").replace("-", "")[:8]
    try:
        age = (datetime.datetime.strptime(slate.replace("-", ""), "%Y%m%d")
               - datetime.datetime.strptime(bd, "%Y%m%d")).days
    except Exception:
        continue
    if not (0 <= age <= 1): continue
    pl, mk = (b.get("player") or "").lower(), b.get("market")
    if mk not in MKTS: continue
    tm = teamnow.get(pl)
    if tm not in tips or (pl, mk) in seen: continue
    tonight = bygame.get((pl, mk, tips[tm]), [])
    if not tonight: continue
    seen.add((pl, mk))
    line_now, price_now = tonight[-1][1], tonight[-1][2]
    earlier = sorted(g for (p2, m2, g) in bygame if p2 == pl and m2 == mk and g < tips[tm])
    pv = bygame[(pl, mk, earlier[-1])][-1][1] if earlier else None
    same = [x for x in tonight if x[1] == line_now]
    drift = same[-1][2]/same[0][2] - 1 if len(same) >= 2 else 0.0
    C.append(dict(pl=pl, name=b.get("player"), mk=mk, src=b.get("src") or "?", tip=tips[tm],
                  line=line_now, odds=price_now, prev=pv, drift=drift,
                  raised=(pv is None or line_now - pv >= 0.5),   # no prev line is NOT a star
                  noprev=(pv is None),
                  mv=(None if pv is None else line_now - pv),
                  tier=b.get("tier") or "",
                  nodrift=(drift < 0.01)))

# ---- the competing rules ----------------------------------------------------------------------
# MODEL_S is the live one. Everything else is a rejected filter kept on paper so that in six
# weeks the choice is made by forward data rather than by whichever backtest I ran last.
CONFIGS = {
    "MODEL_S":  lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and not r["raised"],
    "S_drift":  lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and r["nodrift"],
    "S_filterx":lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and not r["raised"] and r["nodrift"],
    "S_nostar": lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS,
    "S_prev":   lambda r: r["src"] in ("flip","hotover") and r["mk"] in BET_MKTS and not r["raised"],
    "S_raised": lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and r["raised"],
    # S_loose: allow a ONE-POINT raise. Backtest said +17.3% on the big universe and -10.7% on
    # the strict one - the same band, opposite signs, because the two differ only in how a bet's
    # line is chosen. Not live for exactly that reason; tracked so forward data can settle it.
    "S_loose":  lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS
                          and not r["noprev"] and r["mv"] is not None and r["mv"] < 2.0,
    # S_noprev: the group that used to be silently bet as starred (48.4%, -10.0%). Tracked as a
    # control - if it stops losing, the exclusion needs revisiting.
    "S_noprev": lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and r["noprev"],
    # S_paper: flip_paper restricted to the engine's THIN and STRONG confidence tiers. This is the
    # best-evidenced candidate found so far and it is still NOT live. In its favour: n=69, 68.1%,
    # +26.6% ROI, both time-halves positive (IN +39.8% / OUT +17.6%), a tier-label permutation
    # test at p=0.027, and adding it to Model S raises ROI 24.0% -> 25.0% while lifting volume
    # 2.02 -> 3.30 bets a night. Against it, and decisive:
    #   * NON-MONOTONIC in the engine's own confidence. tier is defined as STRONG p>=0.66,
    #     SOLID p>=0.58, THIN below. Results run THIN +34.8%, SOLID -13.9%, STRONG +19.5% -
    #     good, bad, good across an ORDERED variable. That is the shape of noise, not signal.
    #   * DECAYING: June +51.1%, July +35.9%, August +4.2%. The most recent month is flat.
    #   * The star does nothing here (+27.9% vs +25.4%), so adopting it means running a second,
    #     different rule alongside the star - more surface for a fitted result to hide in.
    # A p-value on a split chosen after looking is weaker than three structural objections.
    # Tracked so forward data can overrule me.
    "S_paper":  lambda r: r["src"] == "flip_paper" and r["mk"] in BET_MKTS
                          and r.get("tier") in ("THIN", "STRONG"),
    "OLD_MENU": lambda r: True,
}

def one_position(rows):
    """same player, two markets = ONE position (the live staking rule)"""
    best = {}
    for r in sorted(rows, key=lambda x: -x["odds"]):
        best.setdefault(r["pl"], r)
    return sorted(best.values(), key=lambda r: r["name"])

rows_all = load("shadow_forward.csv")
# THE WINDOW NARROWS AS GAMES TIP, AND THAT USED TO DESTROY ROWS. `tips` only holds games still
# ahead of us, so once the 21:00 games start, first_tip jumps to the 23:00 game and the pre-tip
# rewrite fires AGAIN - but now only the late game's players are candidates, so the earlier ones
# were silently dropped. On 2026-08-16 the card logged 3 Model S bets and this file kept 1.
# Fix: identify a row by its GAME (player, market, tip), never rewrite a row whose game has
# already started, and only replace rows for games still ahead.
def _tipkey(t): return t.strftime("%Y-%m-%dT%H:%MZ")
live_tips = {_tipkey(t) for t in tips.values() if NOW < t}
keep = [r for r in rows_all
        if (r.get("result") or "") != "" or r.get("tip", "") not in live_tips]
have = {(r.get("config"), r.get("player"), r.get("market"), r.get("tip")) for r in keep}

stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
added = collections.Counter()
for cfg, fn in CONFIGS.items():
    picks = [r for r in C if fn(r)]
    if cfg != "OLD_MENU": picks = one_position(picks)
    for r in picks:
        tk = _tipkey(r["tip"])
        if NOW >= r["tip"]: continue                       # her game has started - never add
        if (cfg, r["name"], r["mk"], tk) in have: continue  # already recorded for THIS game
        keep.append({"slate": slate, "config": cfg, "player": r["name"], "market": r["mk"],
                     "line": r["line"], "odds": r["odds"], "src": r["src"],
                     "prev_line": "" if r["prev"] is None else r["prev"],
                     "mv": "" if r.get("mv") is None else r["mv"],
                     "drift": f"{r['drift']:.4f}", "tip": _tipkey(r["tip"]),
                     "logged_utc": stamp,
                     "result": "", "actual": ""})
        added[cfg] += 1

tmp = OUT + ".tmp"
with open(tmp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for r in keep: w.writerow({c: r.get(c, "") for c in COLS})
os.replace(tmp, OUT)                                  # atomic - never a half-written file

# ---- THE PARLAY LEDGER --------------------------------------------------------------------------
# A real record, written at decision time, rather than something re-derived later from the singles.
# Pairing matches model_card.py exactly: Model S picks sorted by TIP, paired consecutively, no leg
# reused, odd bet left out.
#
# same_game is recorded because the audit could not settle whether it matters on RESULTS - 148
# historical pairs gave same-game 45.5% vs different-game 31.7% against a 29.2% break-even, but a
# permutation test put that gap at p=0.55. What IS settled is the mechanism: our player overs are
# a de facto bet on the GAME going over its total.
#     game went over its total   n=20  75.0%  ROI +38.4%
#     game went under            n=21  42.9%  ROI -21.7%
# and our signal does NOT predict which way that goes (13 over / 13 under across 26 games). So the
# game-total exposure is UNCOMPENSATED - it swings results hard and we have no edge on direction.
# That makes different-game pairs preferable on risk grounds alone, no data-mining needed:
# spreading legs across games diversifies an exposure we cannot forecast.
PAR = os.path.join(D, "parlay_forward.csv")
PCOLS = ["slate", "leg1", "mk1", "line1", "odds1", "leg2", "mk2", "line2", "odds2",
         "combined_odds", "same_game", "logged_utc", "result", "pnl"]
ms = one_position([r for r in C if CONFIGS["MODEL_S"](r)])
ms = sorted(ms, key=lambda r: (r["tip"], r["name"]))
prev_rows = load("parlay_forward.csv")
if NOW < first_tip:
    pkeep = [r for r in prev_rows if not (r.get("slate") == slate and (r.get("result") or "") == "")]
else:
    pkeep = list(prev_rows)
padded = 0
if NOW < first_tip:
    for i in range(0, len(ms) - 1, 2):
        a, b2 = ms[i], ms[i + 1]
        pkeep.append({"slate": slate, "leg1": a["name"], "mk1": a["mk"], "line1": a["line"],
                      "odds1": a["odds"], "leg2": b2["name"], "mk2": b2["mk"], "line2": b2["line"],
                      "odds2": b2["odds"], "combined_odds": round(a["odds"] * b2["odds"], 4),
                      "same_game": int(a["tip"] == b2["tip"]), "logged_utc": stamp,
                      "result": "", "pnl": ""})
        padded += 1
ptmp = PAR + ".tmp"
with open(ptmp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=PCOLS)
    w.writeheader()
    for r in pkeep: w.writerow({c: r.get(c, "") for c in PCOLS})
os.replace(ptmp, PAR)                                 # atomic
if padded:
    print(f"  parlay ledger {slate}: {padded} pair(s) logged")

if added:
    print("  shadow " + slate + ": " + ", ".join(f"{k} {v}" for k, v in sorted(added.items())))
else:
    print(f"  shadow {slate}: no new rows ({'post-tip, frozen' if NOW >= first_tip else 'nothing qualifies'})")
