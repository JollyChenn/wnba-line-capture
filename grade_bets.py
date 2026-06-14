# grade_bets.py — settle the actual logged bets (bets_log.csv) against box-score results.
# Reports hit-rate, ROI, net units, and a line-move CLV proxy. Appends settled bets to graded_bets.csv.
import csv, os
from collections import defaultdict

if not os.path.exists("bets_log.csv"):
    print("no bets logged yet — nothing to grade"); raise SystemExit

# actual results from the box
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

# dedup bets_log -> one bet per (date, player, market, side); last capture = line we'd bet, first = line-move proxy
caps = defaultdict(list)
for b in csv.DictReader(open("bets_log.csv", encoding="utf-8")):
    caps[(b["date"], b["player"].lower(), b["market"], b["side"])].append(
        (b["captured_utc"], float(b["line"]), float(b["odds"]), b.get("tier", ""), b["player"]))

done = set()
if os.path.exists("graded_bets.csv"):
    for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
        done.add((r["date"], r["player"].lower(), r["market"], r["side"]))

new_rows = []
for (d, plow, mk, side), cl in caps.items():
    if (d, plow, mk, side) in done:
        continue
    act = actual.get((plow, d, mk))
    if act is None:
        continue                                      # game not final / box not updated yet
    cl.sort()
    line, odds, tier, disp = cl[-1][1], cl[-1][2], cl[-1][3], cl[-1][4]
    open_line = cl[0][1]
    if act == line:
        res, pnl = "push", 0.0
    elif (act < line) == (side == "Under"):
        res, pnl = "WIN", odds - 1
    else:
        res, pnl = "loss", -1.0
    move = (open_line - line) if side == "Under" else (line - open_line)   # >0 = line drifted our way after we saw it
    new_rows.append([d, disp, mk, side, line, odds, tier, act, res, round(pnl, 2), round(move, 1)])

if new_rows:
    fnew = not os.path.exists("graded_bets.csv")
    with open("graded_bets.csv", "a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if fnew:
            wr.writerow(["date", "player", "market", "side", "line", "odds", "tier", "actual", "result", "pnl", "line_move"])
        wr.writerows(sorted(new_rows))
    print(f"settled {len(new_rows)} new bet(s)")
else:
    print("no new bets to settle (games not final yet)")

allg = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8"))) if os.path.exists("graded_bets.csv") else []
dec = [g for g in allg if g["result"] in ("WIN", "loss")]
if not dec:
    print("no settled bets yet — track record starts after tonight's games"); raise SystemExit
n = len(dec); w = sum(1 for g in dec if g["result"] == "WIN"); net = sum(float(g["pnl"]) for g in dec)
mv = sum(float(g["line_move"]) for g in allg) / len(allg)
print(f"\n===== TRACK RECORD ({n} settled) =====")
print(f"  hit-rate : {w}/{n} = {w / n * 100:.0f}%")
print(f"  net P&L  : {net:+.2f}u  (ROI {net / n * 100:+.1f}%/bet)")
print(f"  CLV proxy (avg line drift our way): {mv:+.2f}")
for label, keyf in [("market/side", lambda g: f"{g['market']} {g['side']}"), ("tier", lambda g: g["tier"] or "?")]:
    by = defaultdict(lambda: [0, 0])
    for g in dec:
        by[keyf(g)][0] += 1; by[keyf(g)][1] += g["result"] == "WIN"
    print(f"  by {label}:")
    for k, (t, ww) in sorted(by.items()):
        print(f"     {k:13} {ww}/{t} = {ww / t * 100:.0f}%")
