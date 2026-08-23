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
import csv, os, sys, datetime, collections, statistics, unicodedata, re
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
# --asof <ISO> replays this script as if it were running at a past moment, so a slate missed
# while the laptop was off can still be recorded. EVERY data source below is then capped at NOW:
# the board, bets_log, the sharp lines and the box-score history. Without those caps a replay
# would quietly use the final board state and post-game box scores, which is the "reconstructed
# later" failure the shadow log exists to avoid.
#
# A replayed row is NOT as good as a live one - it proves the rule would have SELECTED the bet,
# but not that we were awake to place it. Rows are stamped backfill=1 and grade_shadow reports
# the two populations separately. Never trust a config whose record is mostly backfill.
ASOF = None
_args = [a for a in sys.argv[1:]]
if "--asof" in _args:
    i = _args.index("--asof")
    try:
        ASOF = datetime.datetime.fromisoformat(_args[i+1].replace("Z", "+00:00"))
        del _args[i:i+2]
    except Exception:
        print("  shadow: bad --asof value"); raise SystemExit
NOW = ASOF or datetime.datetime.now(datetime.timezone.utc)
BACKFILL = "1" if ASOF else ""
WINDOW_H = float(_args[0]) if _args else 16.0
MKTS = ("pts", "pra", "pr", "pa", "reb", "ast", "ra")
BET_MKTS = ("pra", "pr", "pts")
SIGS = ("flip", "hotover", "overshoot")
OUT = os.path.join(D, "shadow_forward.csv")
# `side` and `gap` added 2026-08-21 for the sharp-divergence configs. Every config before them
# bets the OVER, so a row with no side is read as "Over" by grade_shadow - old rows stay valid.
COLS = ["slate", "config", "player", "market", "side", "line", "odds", "src",
        "prev_line", "mv", "drift", "gap", "tip", "logged_utc", "backfill", "result", "actual"]

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
    if not t or t > NOW: continue                       # --asof cap: never see the future board
    if o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))

# BOX HISTORY IS CAPPED AT THE SLATE. In a replay the box file already contains the very games
# we are pretending not to know about, so every box-derived feature (team, scoring rank, market
# volatility) is restricted to games played BEFORE this slate. In the live case this is a no-op.
_slatekey = slate.replace("-", "")
teamnow = {}
gm = {g.get("game_id"): g.get("date","") for g in load("data/games_2026.csv")
      if (g.get("date") or "") < _slatekey}
for r in load("data/box_2026.csv"):
    if gm.get(r.get("game_id")): teamnow[(r.get("player") or "").lower()] = r.get("team")

# ---- SCORING RANK inside her own team, from her last 6 games ------------------------------------
# The full-board sweep found exactly two cells that held out of sample: the team's SECOND scorer's
# OVER (+3.2%, IN +1.8 -> OUT +4.5) and the FOURTH scorer's UNDER (+5.1%, IN +6.5 -> OUT +4.2).
# Neither is live. Both are non-monotonic in rank - a spike with negative neighbours - and the
# global permutation that produced them (p=0.0207) prices only the 74 cells inside that one grid,
# not the forty-odd scripts run before it. Recording them here is the cheap way to find out: in
# six weeks the forward column answers it, and no backtest has to be trusted.
# Only the rank-2 OVER can be tracked in this file - every candidate row here is an over. The
# rank-4 UNDER needs an under-side ledger that does not exist yet.
_pgames = collections.defaultdict(list)
for r in load("data/box_2026.csv"):
    d = gm.get(r.get("game_id"))
    if not d: continue
    try: p_ = float(r.get("pts") or 0)
    except ValueError: continue
    _pgames[(r.get("player") or "").lower()].append((d, r.get("team"), p_))
_avg = {}
for pl, v in _pgames.items():
    v.sort()
    last = v[-6:]
    if last: _avg[pl] = sum(x[2] for x in last)/len(last)
_byteam = collections.defaultdict(list)
for pl, a in _avg.items():
    if teamnow.get(pl): _byteam[teamnow[pl]].append((a, pl))
RANK = {}
for tm, v in _byteam.items():
    for i, (a, pl) in enumerate(sorted(v, reverse=True), 1): RANK[pl] = i

# ---- per-market history for S_steady's volatility read (current-team games only - the same
# filter overshoot_overs applies; an unfiltered median already burned us once on All-Star games)
_mkhist = collections.defaultdict(list)          # (player, market) -> [value, ...] time-ordered
for r in load("data/box_2026.csv"):
    d = gm.get(r.get("game_id"))
    if not d: continue
    try:
        p_, rb, a_ = float(r.get("pts") or 0), float(r.get("reb") or 0), float(r.get("ast") or 0)
    except ValueError:
        continue
    pl = (r.get("player") or "").lower()
    if r.get("team") != teamnow.get(pl): continue
    vals = {"pts": p_, "reb": rb, "ast": a_, "pr": p_+rb, "pa": p_+a_, "ra": rb+a_, "pra": p_+rb+a_}
    for mk2, vv in vals.items(): _mkhist[(pl, mk2)].append((d, vv))
def relvol_of(pl, mk, line):
    v = sorted(_mkhist.get((pl, mk), []))
    if len(v) < 6 or not line: return None
    w = [x[1] for x in v[-10:]]
    return statistics.pstdev(w) / max(float(line), 1.0)

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

# ---- UNDER prices, needed only by the divergence configs --------------------------------------
# The loop above keeps OVER quotes because every config written before 2026-08-21 bets the over.
# S_gap follows Pinnacle and can land on either side, and pricing an under at the over's odds
# would silently invent about 7% of edge out of the book's own margin. So the under side of the
# same line is collected separately and looked up at the line we are actually betting.
bygameU = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if not (t and o and ln is not None) or b.get("side") != "Under": continue
    if t > NOW or b.get("market") not in MKTS: continue   # --asof cap
    pl = (b.get("player") or "").lower()
    tm = teamnow.get(pl)
    if tm is None: continue
    gt = game_for(tm, t)
    if gt is None: continue
    bygameU[(pl, b.get("market"), gt)].append((t, ln, o))
for v in bygameU.values(): v.sort()
def under_price(pl, mk, gt, line):
    """the under quote at the SAME line, latest first - None if the book never posted one"""
    same = [x for x in bygameU.get((pl, mk, gt), []) if abs(x[1] - line) < 0.01]
    return same[-1][2] if same else None

# ---- the SHARP reference, for the divergence configs ------------------------------------------
# Bet toward Pinnacle when 1xbet disagrees with it by a point or more. Backtest (gap_final.py):
# toward-sharp return rises with |gap| - rho +0.2503, player-block permutation p = 0.0083, which
# survives Bonferroni over the five families declared in fresh_hunt.py (0.0083 x 5 = 0.042). Both
# directions pay about the same (+13.6% over / +12.4% under) and it holds out of sample
# (+14.5% / +11.4%). Crucially it is NOT the overshoot signal wearing a different hat: stratified
# by cushion it separates in both halves, and gap-with-cushion-under-3 returns +14.3% on n=100 -
# it works precisely where overshoot is blind.
#
# TIMING MATTERS AND IS NOT OPTIONAL. The same rule scored using the sharp line as it stood 12h
# before tip returns -14.9%; using the 6h line, +13.0%. Pinnacle's early prop lines are posted at
# low limits and carry no information. So only captures within SHARP_MAX_AGE_H are trusted, and
# the shadow log runs on the same ~6h cadence as the card.
#
# Names are normalised the way cloud_xbet's _pkey does it (accents folded, punctuation stripped),
# because pinn_board.csv is keyed that way and "A'ja Wilson" must meet "aja wilson".
SHARP_MAX_AGE_H = 10.0
def pkey(name):
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip() or str(name or "").lower()

sharp_raw = collections.defaultdict(list)
for r in load("pinn_board.csv"):                       # full board (added 2026-08-21) - preferred
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn_line"))
    if t and t <= NOW and ln is not None: sharp_raw[(pkey(r.get("player")), r.get("market"))].append((t, ln))
for r in load("bets_log.csv"):                         # engine-bet players only, but has history
    t, ln = ts(r.get("captured_utc")), f(r.get("pinn"))
    if t and t <= NOW and ln is not None: sharp_raw[(pkey(r.get("player")), r.get("market"))].append((t, ln))
for v in sharp_raw.values(): v.sort()
def sharp_line(pl, mk):
    v = sharp_raw.get((pkey(pl), mk), [])
    fresh = [x for x in v if (NOW - x[0]).total_seconds() <= SHARP_MAX_AGE_H*3600]
    return fresh[-1][1] if fresh else None

# ---- candidates, exactly as model_card builds them --------------------------------------------
seen, C = set(), []
for b in load("bets_log.csv"):
    if b.get("side") != "Over": continue
    _bt = ts(b.get("captured_utc"))
    if _bt and _bt > NOW: continue                      # --asof cap: signal not emitted yet
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
    sl = sharp_line(b.get("player"), mk)
    C.append(dict(pl=pl, name=b.get("player"), mk=mk, src=b.get("src") or "?", tip=tips[tm],
                  line=line_now, odds=price_now, prev=pv, drift=drift,
                  raised=(pv is None or line_now - pv >= 0.5),   # no prev line is NOT a star
                  noprev=(pv is None),
                  mv=(None if pv is None else line_now - pv),
                  tier=b.get("tier") or "",
                  rank=RANK.get(pl, 99),
                  sharp=sl,
                  gap=(None if sl is None else round(sl - line_now, 2)),
                  uodds=under_price(pl, mk, tips[tm], line_now),
                  relvol=relvol_of(pl, mk, line_now),
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
    # S_rank2 / RANK2_ANY: the second-scorer over. S_rank2 is Model S narrowed to her, which
    # should raise ROI and cut volume if the rank cell is real and separate from the star.
    # RANK2_ANY ignores our signals entirely - if THAT one wins, the engine is the part to drop.
    # On the board the two barely differ (rank2 & ever-flagged +4.4%, rank2 never flagged -26.5%),
    # but that split is 105 quotes deep on the second arm and cannot carry the claim.
    "S_rank2":  lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and not r["raised"]
                          and r.get("rank") == 2,
    "RANK2_ANY":lambda r: r["mk"] in BET_MKTS and r.get("rank") == 2,
    # S_gap / S_gap_big: bet TOWARD Pinnacle whenever 1xbet's line disagrees with it. The first
    # thing all season to show a dose-response rather than a cell - toward-sharp return rises with
    # |gap| (rho +0.2503, player-block permutation p = 0.0083, Bonferroni over 5 declared families
    # = 0.042) - to pay symmetrically on BOTH sides (+13.6% over / +12.4% under), and to hold out
    # of sample (+14.5% then +11.4%). It is also demonstrably not the overshoot signal renamed:
    # inside the shallow-cushion half it returns +14.3% on n=100, where overshoot never fires.
    # NOT LIVE. The backtest reaches only 150 genuine disagreements, almost all pts, because until
    # today we only wrote down Pinnacle lines for players we had already bet. cloud_xbet now logs
    # the whole sharp board, so this config's own forward record is what will settle it.
    # Requires an under price when it points down - no quote, no bet, rather than a guessed price.
    "S_gap":    lambda r: r.get("gap") is not None and abs(r["gap"]) >= 1.0
                          and (r["gap"] > 0 or r.get("uodds")),
    "S_gap_big":lambda r: r.get("gap") is not None and abs(r["gap"]) >= 1.5
                          and (r["gap"] > 0 or r.get("uodds")),
    # S_gap_x: the divergence restricted to bets Model S would ALSO take. If the two are the same
    # information this matches MODEL_S; if they are independent it should beat both.
    "S_gap_x":  lambda r: r.get("gap") is not None and r["gap"] >= 1.0
                          and r["src"] in SIGS and r["mk"] in BET_MKTS and not r["raised"],
    # S_steady: Model S minus the wild tercile. The volatility gradient is the only board-wide
    # cell with a CI excluding zero (wild overs -12.0% [-17.2,-7.2]) and it reaches Model S:
    # steady +12.4 / mid +11.2 / wild +0.1 (n=96). vol_filter.py then tried 15 declared rescues
    # and NONE cleared a +9.0% ceiling - wild overs are unrescuable by any tested context, and
    # wild unders top out at breakeven (the margin wall). So the actionable form is subtraction:
    # skip the wild third. Tracked here, not live - ~32 bets per tercile is not a gating sample.
    "S_steady": lambda r: r["src"] in SIGS and r["mk"] in BET_MKTS and not r["raised"]
                          and r.get("relvol") is not None and r["relvol"] <= 0.446,
    "OLD_MENU": lambda r: True,
}

# Which SIDE each config bets, and therefore which price it is scored at. Everything written
# before 2026-08-21 is an over; only the divergence configs can point down, and they follow the
# sign of the gap. grade_shadow reads a missing side as "Over" so historical rows are unaffected.
def side_of(cfg, r):
    if cfg in ("S_gap", "S_gap_big") and r.get("gap") is not None and r["gap"] < 0:
        return "Under"
    return "Over"
def odds_of(cfg, r):
    return r["uodds"] if (side_of(cfg, r) == "Under" and r.get("uodds")) else r["odds"]

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
                     "side": side_of(cfg, r),
                     "line": r["line"], "odds": odds_of(cfg, r), "src": r["src"],
                     "prev_line": "" if r["prev"] is None else r["prev"],
                     "mv": "" if r.get("mv") is None else r["mv"],
                     "drift": f"{r['drift']:.4f}",
                     "gap": "" if r.get("gap") is None else r["gap"],
                     "tip": _tipkey(r["tip"]),
                     "logged_utc": stamp, "backfill": BACKFILL,
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
