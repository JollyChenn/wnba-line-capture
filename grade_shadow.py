# grade_shadow.py - settle the shadow log and print the head-to-head scoreboard.
# ---------------------------------------------------------------------------------------------
# shadow_log.py records what each competing rule would have bet, at decision time. This fills in
# the outcomes and shows all of them side by side, so that in six weeks the choice between
# MODEL_S and its rejected alternatives is made by forward data.
#
# Reads the box score fresh for recent slates (a cached box can be a game behind - that is how a
# Wheeler assist went missing once and graded a win as a loss).
import csv, os, sys, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
FWD = os.path.join(D, "shadow_forward.csv")
if not os.path.exists(FWD):
    print("  no shadow_forward.csv yet"); raise SystemExit

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

gm = {g.get("game_id"): g.get("date", "") for g in load("data/games_2026.csv")}
box = {}
for r in load("data/box_2026.csv"):
    d = gm.get(r.get("game_id"))
    if not d: continue
    p_, rb, a = f(r.get("pts")) or 0, f(r.get("reb")) or 0, f(r.get("ast")) or 0
    box[(d, (r.get("player") or "").strip().lower())] = dict(
        pts=p_, reb=rb, ast=a, pra=p_+rb+a, pr=p_+rb, pa=p_+a, ra=rb+a)

rows = load("shadow_forward.csv")
graded = 0
for r in rows:
    if (r.get("result") or ""): continue
    day = (r.get("slate") or "").replace("-", "")
    act = box.get((day, (r.get("player") or "").strip().lower()))
    ln = f(r.get("line"))
    if not act or ln is None: continue
    v = act.get(r.get("market"))
    if v is None: continue
    r["result"] = "push" if v == ln else ("WIN" if v > ln else "loss")
    r["actual"] = v
    graded += 1

COLS = ["slate", "config", "player", "market", "line", "odds", "src",
        "prev_line", "drift", "logged_utc", "result", "actual"]
tmp = FWD + ".tmp"
with open(tmp, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for r in rows: w.writerow({c: r.get(c, "") for c in COLS})
os.replace(tmp, FWD)                                   # atomic
print(f"  shadow: graded {graded} new, {len(rows)} rows total")

done = [r for r in rows if (r.get("result") or "").upper() in ("WIN", "LOSS", "PUSH")]
if not done:
    print("  shadow: nothing settled yet"); raise SystemExit

def pnl(r):
    res = (r.get("result") or "").upper()
    if res == "PUSH": return 0.0
    o = f(r.get("odds")) or 1.85
    return (o - 1) if res == "WIN" else -1.0

ORDER = ["MODEL_S", "S_prev", "S_drift", "S_filterx", "S_nostar", "S_raised", "OLD_MENU"]
slates = sorted({r["slate"] for r in done})
print("")
print("=" * 96)
print(f"  SHADOW SCOREBOARD - {len(slates)} settled slate(s), {slates[0]} to {slates[-1]}")
print("  MODEL_S is live. The rest are filters that were rejected on backtest and are being")
print("  tracked forward so the decision is eventually made by real data.")
print("=" * 96)
print(f"  {'config':<11} {'record':>8} {'win%':>7} {'units':>9} {'ROI':>8} {'bets/slate':>11}")
for cfg in ORDER:
    g = [r for r in done if r["config"] == cfg]
    if not g:
        print(f"  {cfg:<11} {'-':>8}"); continue
    w = sum(1 for r in g if (r["result"] or "").upper() == "WIN")
    l = sum(1 for r in g if (r["result"] or "").upper() == "LOSS")
    u = sum(pnl(r) for r in g)
    tag = "  <- LIVE" if cfg == "MODEL_S" else ""
    print(f"  {cfg:<11} {f'{w}-{l}':>8} {100*w/len(g):6.1f}% {u:+8.2f}u {100*u/len(g):+7.1f}%"
          f" {len(g)/len(slates):10.1f}{tag}")
print("")
print("  n is tiny. This table is not evidence yet - it is a record being built. The point at")
print("  which it starts to mean anything is ~50 bets on MODEL_S.")
