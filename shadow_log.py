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
        "prev_line", "drift", "logged_utc", "result", "actual"]

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

# ---- board, split into nights ----------------------------------------------------------------
raw = collections.defaultdict(list)
for b in load("xbet_board.csv"):
    t, o, ln = ts(b.get("captured_utc")), f(b.get("odds")), f(b.get("line"))
    if t and o and ln is not None and b.get("market") in MKTS and b.get("side") == "Over":
        raw[((b.get("player") or "").lower(), b.get("market"), ln)].append((t, o))
nights = collections.defaultdict(list)
for (pl, mk, ln), v in raw.items():
    v.sort(); blocks, cur = [], [v[0]]
    for a_, b_ in zip(v, v[1:]):
        if (b_[0]-a_[0]).total_seconds() > 12*3600: blocks.append(cur); cur = []
        cur.append(b_)
    blocks.append(cur)
    for blk in blocks:
        if blk: nights[(pl, mk)].append((blk[0][0], ln, blk))
for v in nights.values(): v.sort()

teamnow = {}
gm = {g.get("game_id"): g.get("date","") for g in load("data/games_2026.csv")}
for r in load("data/box_2026.csv"):
    if gm.get(r.get("game_id")): teamnow[(r.get("player") or "").lower()] = r.get("team")

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
    tn = [x for x in nights.get((pl, mk), [])
          if (tips[tm] - x[0]).total_seconds() < 30*3600 and x[0] <= tips[tm]]
    if not tn: continue
    seen.add((pl, mk))
    _, line_now, series = max(tn, key=lambda x: len(x[2]))
    prev = [x for x in nights.get((pl, mk), []) if (tips[tm] - x[0]).total_seconds() >= 30*3600]
    pv = prev[-1][1] if prev else None
    drift = series[-1][1]/series[0][1] - 1 if len(series) >= 2 else 0.0
    C.append(dict(pl=pl, name=b.get("player"), mk=mk, src=b.get("src") or "?",
                  line=line_now, odds=series[-1][1], prev=pv, drift=drift,
                  raised=(pv is not None and line_now - pv >= 0.5),
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
    "OLD_MENU": lambda r: True,
}

def one_position(rows):
    """same player, two markets = ONE position (the live staking rule)"""
    best = {}
    for r in sorted(rows, key=lambda x: -x["odds"]):
        best.setdefault(r["pl"], r)
    return sorted(best.values(), key=lambda r: r["name"])

rows_all = load("shadow_forward.csv")
# PRE-TIP REWRITE, same discipline as model_card: a pick can qualify at 21:00 and fail at 22:00
# because the book moved her number. While the slate has not tipped, this slate's ungraded rows
# are replaced by the current view. After first tip they freeze, because by then the bet is real.
if NOW < first_tip:
    keep = [r for r in rows_all
            if not (r.get("slate") == slate and (r.get("result") or "") == "")]
else:
    keep = list(rows_all)
    have = {(r.get("slate"), r.get("config"), r.get("player"), r.get("market")) for r in rows_all}

stamp = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
added = collections.Counter()
for cfg, fn in CONFIGS.items():
    picks = [r for r in C if fn(r)]
    if cfg != "OLD_MENU": picks = one_position(picks)
    for r in picks:
        if NOW >= first_tip and (slate, cfg, r["name"], r["mk"]) in have: continue
        if NOW >= first_tip: continue          # never add a new bet after tip
        keep.append({"slate": slate, "config": cfg, "player": r["name"], "market": r["mk"],
                     "line": r["line"], "odds": r["odds"], "src": r["src"],
                     "prev_line": "" if r["prev"] is None else r["prev"],
                     "drift": f"{r['drift']:.4f}", "logged_utc": stamp,
                     "result": "", "actual": ""})
        added[cfg] += 1

tmp = OUT + ".tmp"
with open(tmp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for r in keep: w.writerow({c: r.get(c, "") for c in COLS})
os.replace(tmp, OUT)                                  # atomic - never a half-written file

if added:
    print("  shadow " + slate + ": " + ", ".join(f"{k} {v}" for k, v in sorted(added.items())))
else:
    print(f"  shadow {slate}: no new rows ({'post-tip, frozen' if NOW >= first_tip else 'nothing qualifies'})")
