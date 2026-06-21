# grade_bets.py — settle logged bets (bets_log.csv) vs box results, with PROPER CLV.
# "Our bet" = the FIRST capture (earliest alert = take-on-sight). "Close" = the LAST capture (near tip).
# Reports hit-rate, ROI, and THREE CLVs: odds-CLV (price moved our way), line-CLV, and sharp-CLV vs Pinnacle.
import csv, os, datetime
from collections import defaultdict

if not os.path.exists("bets_log.csv"):
    print("no bets logged yet — nothing to grade"); raise SystemExit

gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
actual = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gd.get(r["game_id"])
    if not d:
        continue
    try:
        p, rb, a = float(r["pts"]), float(r["reb"]), float(r["ast"])
    except (ValueError, TypeError):
        continue
    for mk, v in {"pts": p, "pr": p + rb, "pa": p + a, "ra": rb + a, "pra": p + rb + a}.items():
        actual[(r["player"].lower(), d, mk)] = v

caps = defaultdict(list)
for b in csv.DictReader(open("bets_log.csv", encoding="utf-8")):
    d = b["date"].replace("-", "")                 # bets_log 2026-06-14 -> box 20260614
    # src (model/flip = proven; hotover/overshoot = unproven overs) flows through to graded_bets so the
    # headline track record + CLV verdict only count the PROVEN signals, never speculative captured overs.
    src = b.get("src", "") or ("model" if b["side"] == "Under" else "overshoot")   # legacy rows: under=model, over=overshoot
    try:
        ev = float(b.get("ev", "") or 0)               # EV drives the one-bet-per-player dedup (keep the player's top-EV market)
    except (ValueError, TypeError):
        ev = 0.0
    caps[(d, b["player"].lower(), b["market"], b["side"])].append(
        (b["captured_utc"], float(b["line"]), float(b["odds"]), b.get("tier", ""), b["player"], b.get("pinn", ""), src, ev))

# RESOLVE TO THE REAL GAME DATE so every capture of a bet is counted (full open->close CLV) -- now TIP-AWARE.
# A line captured AFTER a game has tipped cannot be a bet on that game; it's a line for the player's NEXT game
# (e.g. the every-3h cloud scan at ~05:13 UTC, after the night's games ended, logs tomorrow's lines under today's
# LA slate). The old "earliest box-date >= slate" then MIS-SETTLED those against the FINISHED game. Fix: resolve to
# the earliest game whose TIP is after the bet's first capture, and drop any capture taken at/after that tip. A bet
# captured after every known game tipped -> future game -> stays PENDING (never graded against a finished game).
gt = {r["game_id"]: (r.get("tip") or "") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
player_dates = defaultdict(set)                        # (player, market) -> {dates the player has a FINAL box result}
player_tip = {}                                        # (player, gamedate) -> that game's tip (ISO)
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    dd = gd.get(r["game_id"])
    if dd:
        player_tip[(r["player"].lower(), dd)] = gt.get(r["game_id"], "")
for (plow, dd, mk) in actual:
    player_dates[(plow, mk)].add(dd)


def game_date(plow, mk, slate, first_cap=""):
    for d in sorted(x for x in player_dates.get((plow, mk), ()) if x >= slate):
        tip = player_tip.get((plow, d), "")
        if not tip or not first_cap or tip[:16] > first_cap[:16]:   # captured BEFORE this game tipped -> it's this game
            return d
    return "99999999"                                  # captured after every known game tipped -> future game -> pending


merged = defaultdict(list)                              # collapse cross-midnight captures of the SAME bet (tip-aware)
for (d, plow, mk, side), cl in caps.items():
    first_cap = min(c[0] for c in cl)                  # earliest capture in this slate group
    gdate = game_date(plow, mk, d, first_cap)
    tip = player_tip.get((plow, gdate), "")
    kept = [c for c in cl if (not tip) or c[0][:16] < tip[:16]]   # drop captures at/after the game's tip (next-game lines)
    if kept:
        merged[(gdate, plow, mk, side)].extend(kept)
caps = merged                                          # everything downstream now groups by GAME date

# PINNACLE vig-free FAIR ODDS (sidecar pinn_snapshots.csv) -> sharp ODDS-CLV: our price vs the sharp's fair price.
# Singles only (pts/reb/ast); the LAST capture of each bet = Pinnacle's near-tip "close" fair number. Re-keyed to the
# real game date exactly like the captures above so an evening-before "open" snapshot lands on the right game.
pinn_odds = {}                                          # (game_date, player, market, side) -> (pinn_line, pinn_fair) at close
if os.path.exists("pinn_snapshots.csv"):
    _ps = defaultdict(list)
    for r in csv.DictReader(open("pinn_snapshots.csv", encoding="utf-8")):
        plow = r["player"].lower()
        gd2 = game_date(plow, r["market"], r["date"].replace("-", ""), r["captured_utc"])
        _ps[(gd2, plow, r["market"], r["side"])].append((r["captured_utc"], r.get("pinn_line", ""), r.get("pinn_fair", "")))
    for k, lst in _ps.items():
        lst.sort()
        pinn_odds[k] = (lst[-1][1], lst[-1][2])         # latest capture = sharp close


def sharp_odds_clv(o_line, o_odds, plow, mk, side, gdate):
    po = pinn_odds.get((gdate, plow, mk, side))         # only the SAME line is price-comparable (line diff is line-CLV's job)
    if not po:
        return ""
    try:
        pl, pf = float(po[0]), float(po[1])
        return round(o_odds / pf - 1, 3) if (abs(pl - o_line) < 0.01 and pf > 0) else ""   # >0 = we beat the sharp's fair price
    except (ValueError, TypeError):
        return ""


def line_clv(our, ref, side):
    try:
        return round((our - float(ref)) if side == "Under" else (float(ref) - our), 1)   # >0 = better line than ref
    except (ValueError, TypeError):
        return ""


# ONE BET PER PLAYER PER DAY: among a player's markets on a date, keep only the single highest-EV one.
# Mirrors the live bot's one-line-per-player rule so the graded RECORD isn't inflated by the same player's
# PRA/PR/PA/PTS all being counted (Plum x4 / Howard x2 were re-inflating the experimental overshoot loss tally
# to a fake 1/10 every time this re-ran). EV is the tiebreak (the bet the bot would actually have placed).
best = {}                                              # (date, player) -> (market, side, ev) of the top-EV bet that day
for (d, plow, mk, side), cl in caps.items():
    if any(x[6] == "cascade" for x in cl):
        continue                                       # cascade legs are EXEMPT from the one-per-player contest (a distinct
                                                       # star-out PRA over) -- never let them displace, or be displaced by, a model bet
    ev = max(x[7] for x in cl)
    if (d, plow) not in best or ev > best[(d, plow)][2]:
        best[(d, plow)] = (mk, side, ev)

# Full REBUILD each run (idempotent): graded_bets is derived from bets_log + box, so regrading from scratch
# is safe, always applies the dedup, and never leaves stale duplicate rows from older append-only runs.
rows = []
for (d, plow, mk, side), cl in caps.items():
    is_casc = any(x[6] == "cascade" for x in cl)       # cascade exempt: graded as its own experimental over
    if not is_casc and (mk, side) != best[(d, plow)][:2]:
        continue                                       # not this player's top-EV market that day -> drop (one bet per player)
    act = actual.get((plow, d, mk))
    if act is None:
        continue                                       # game not final yet -> pending
    cl.sort()
    o_line, o_odds, tier, disp = cl[0][1], cl[0][2], cl[0][3], cl[0][4]      # OUR bet = first alert (opening line + price)
    o_src = cl[0][6]                                                          # signal source of OUR (first) capture
    # CLOSE PRICE = the last capture STILL AT OUR OPENING LINE. The soft book oscillates the price (1.91<->2.0) and
    # sometimes shifts the line (e.g. 14.5->15.5); taking the absolute-last capture made the odds-CLV BOUNCE and could
    # even compare our 14.5 open against a 15.5 close. Locking the close to OUR line keeps it apples-to-apples and
    # STABLE -- it stops moving once captures end after tip. (Real-money entry/close odds live in my_bets.csv,
    # hand-entered and never recomputed -- this only affects the bot's SIGNAL CLV.)
    at_line = [c for c in cl if c[1] == o_line]                              # captures still at our opening line
    c_odds, c_pinn = at_line[-1][2], at_line[-1][5]                          # closing PRICE + sharp ref AT our line
    c_line = cl[-1][1]                                                        # true last line (line MOVE itself is real signal -> line-CLV)
    has_close = len(at_line) >= 2                                            # need >=2 captures AT OUR LINE for a measured close
    if act == o_line:
        res, pnl = "push", 0.0
    elif (act < o_line) == (side == "Under"):
        res, pnl = "WIN", o_odds - 1
    else:
        res, pnl = "loss", -1.0
    odds_clv = round(o_odds / c_odds - 1, 3) if (c_odds and has_close) else ""   # opening price vs CLOSING price AT OUR LINE (stable)
    line_self = line_clv(o_line, c_line, side) if len(cl) >= 2 else ""           # line drift open->close (uses the true last line)
    rows.append([d, disp, mk, side, o_line, o_odds, tier, act, res, round(pnl, 2),
                 odds_clv, line_self, line_clv(o_line, c_pinn, side),
                 sharp_odds_clv(o_line, o_odds, plow, mk, side, d), o_src])   # sharp line+odds CLV; src for honest split

with open("graded_bets.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.writer(f)
    wr.writerow(["date", "player", "market", "side", "line", "odds", "tier", "actual", "result", "pnl",
                 "odds_clv", "line_clv", "sharp_clv", "sharp_odds_clv", "src"])
    wr.writerows(sorted(rows))
print(f"graded {len(rows)} settled bet(s) (one-per-player-per-day, rebuilt from bets_log)")

allg = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8"))) if os.path.exists("graded_bets.csv") else []
def _src(g):                                          # legacy graded rows (no src col): under=model, over=overshoot
    return g.get("src", "") or ("model" if g["side"] == "Under" else "overshoot")
PROVEN = {"model"}                                    # headline = REAL-MONEY signal ONLY (COLD/SHRINK/STINGY); flip/etc = paper
decided = [g for g in allg if g["result"] in ("WIN", "loss")]
dec = [g for g in decided if _src(g) in PROVEN]       # speculative overs (hotover/overshoot) are reported SEPARATELY
exp = [g for g in decided if _src(g) not in PROVEN]
if exp:                                               # always surface the unproven overs, but NEVER in the headline
    by = defaultdict(lambda: [0, 0, 0.0])
    for g in exp:
        by[_src(g)][0] += 1; by[_src(g)][1] += g["result"] == "WIN"; by[_src(g)][2] += float(g["pnl"])
    print("  PAPER / experimental (UNPROVEN, not in headline): "
          + " · ".join(f"{k} {ww}/{t} ({p:+.1f}u)" for k, (t, ww, p) in sorted(by.items())))
if not dec:
    print("no PROVEN-signal bets settled yet — headline track record starts when a cold+shrink under/flip settles"); raise SystemExit
n = len(dec); w = sum(1 for g in dec if g["result"] == "WIN"); net = sum(float(g["pnl"]) for g in dec)
print(f"\n===== TRACK RECORD — PROVEN signals only ({n} settled) =====")
print(f"  hit-rate : {w}/{n} = {w / n * 100:.0f}%")
print(f"  net P&L  : {net:+.2f}u  (ROI {net / n * 100:+.1f}%/bet)")
proven_rows = [g for g in allg if _src(g) in PROVEN]   # CLV headline also restricted to proven signals
# THE PROOF HIERARCHY: sharp ODDS-CLV (beat Pinnacle's fair price) > sharp LINE-CLV (better number than sharp) >
# self ODDS-CLV (just timed 1xbet's own move = weakest). Print all so we can study them side by side.
soc = [float(g["sharp_odds_clv"]) for g in proven_rows if g.get("sharp_odds_clv") not in ("", None)]
if soc:
    sb = sum(1 for x in soc if x > 0)
    print(f"  ★ SHARP ODDS-CLV vs Pinnacle fair price: {sum(soc) / len(soc) * 100:+.1f}% avg | beat fair {sb}/{len(soc)} ({sb / len(soc) * 100:.0f}%)   <- TRUE edge test")
sc = [float(g["sharp_clv"]) for g in proven_rows if g.get("sharp_clv") not in ("", None)]
if sc:
    sbl = sum(1 for x in sc if x > 0)
    print(f"    SHARP LINE-CLV vs Pinnacle line: {sum(sc) / len(sc):+.2f} pts avg | better {sbl}/{len(sc)} ({len(sc)} bets, combos incl.)")
oc = [float(g["odds_clv"]) for g in proven_rows if g.get("odds_clv") not in ("", None)]
if oc:
    beat = sum(1 for x in oc if x > 0)
    print(f"    self ODDS-CLV vs 1xbet's own close: {sum(oc) / len(oc) * 100:+.1f}% avg | beat {beat}/{len(oc)} ({beat / len(oc) * 100:.0f}%)   (soft-book self-close = weak)")
for label, keyf in [("market/side", lambda g: f"{g['market']} {g['side']}"), ("tier", lambda g: g["tier"] or "?")]:
    by = defaultdict(lambda: [0, 0])
    for g in dec:
        by[keyf(g)][0] += 1; by[keyf(g)][1] += g["result"] == "WIN"
    print(f"  by {label}:")
    for k, (t, ww) in sorted(by.items()):
        print(f"     {k:13} {ww}/{t} = {ww / t * 100:.0f}%")
