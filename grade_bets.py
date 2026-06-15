# grade_bets.py — settle logged bets (bets_log.csv) vs box results, with PROPER CLV.
# "Our bet" = the FIRST capture (earliest alert = take-on-sight). "Close" = the LAST capture (near tip).
# Reports hit-rate, ROI, and THREE CLVs: odds-CLV (price moved our way), line-CLV, and sharp-CLV vs Pinnacle.
import csv, os
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
    caps[(d, b["player"].lower(), b["market"], b["side"])].append(
        (b["captured_utc"], float(b["line"]), float(b["odds"]), b.get("tier", ""), b["player"], b.get("pinn", "")))

done = set()
if os.path.exists("graded_bets.csv"):
    for r in csv.DictReader(open("graded_bets.csv", encoding="utf-8")):
        done.add((r["date"], r["player"].lower(), r["market"], r["side"]))


def line_clv(our, ref, side):
    try:
        return round((our - float(ref)) if side == "Under" else (float(ref) - our), 1)   # >0 = better line than ref
    except (ValueError, TypeError):
        return ""


new_rows = []
for (d, plow, mk, side), cl in caps.items():
    if (d, plow, mk, side) in done:
        continue
    act = actual.get((plow, d, mk))
    if act is None:
        continue
    cl.sort()
    o_line, o_odds, tier, disp = cl[0][1], cl[0][2], cl[0][3], cl[0][4]      # OUR bet = first alert
    c_line, c_odds, c_pinn = cl[-1][1], cl[-1][2], cl[-1][5]                 # CLOSE = last capture
    if act == o_line:
        res, pnl = "push", 0.0
    elif (act < o_line) == (side == "Under"):
        res, pnl = "WIN", o_odds - 1
    else:
        res, pnl = "loss", -1.0
    odds_clv = round(o_odds / c_odds - 1, 3) if c_odds else ""               # >0 = we got a longer price than the close
    new_rows.append([d, disp, mk, side, o_line, o_odds, tier, act, res, round(pnl, 2),
                     odds_clv, line_clv(o_line, c_line, side), line_clv(o_line, c_pinn, side)])

if new_rows:
    fnew = not os.path.exists("graded_bets.csv")
    with open("graded_bets.csv", "a", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        if fnew:
            wr.writerow(["date", "player", "market", "side", "line", "odds", "tier", "actual", "result", "pnl", "odds_clv", "line_clv", "sharp_clv"])
        wr.writerows(sorted(new_rows))
    print(f"settled {len(new_rows)} new bet(s)")
else:
    print("no new bets to settle (games not final yet)")

allg = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8"))) if os.path.exists("graded_bets.csv") else []
dec = [g for g in allg if g["result"] in ("WIN", "loss")]
if not dec:
    print("no settled bets yet — track record starts after tonight's games"); raise SystemExit
n = len(dec); w = sum(1 for g in dec if g["result"] == "WIN"); net = sum(float(g["pnl"]) for g in dec)
print(f"\n===== TRACK RECORD ({n} settled) =====")
print(f"  hit-rate : {w}/{n} = {w / n * 100:.0f}%")
print(f"  net P&L  : {net:+.2f}u  (ROI {net / n * 100:+.1f}%/bet)")
oc = [float(g["odds_clv"]) for g in allg if g.get("odds_clv") not in ("", None)]
if oc:
    beat = sum(1 for x in oc if x > 0)
    print(f"  ODDS CLV : {sum(oc) / len(oc) * 100:+.1f}% avg | beat the close {beat}/{len(oc)} ({beat / len(oc) * 100:.0f}%)   <- THE edge signal")
sc = [float(g["sharp_clv"]) for g in allg if g.get("sharp_clv") not in ("", None)]
if sc:
    print(f"  SHARP CLV vs Pinnacle (line): {sum(sc) / len(sc):+.2f} avg ({len(sc)} points bets)")
for label, keyf in [("market/side", lambda g: f"{g['market']} {g['side']}"), ("tier", lambda g: g["tier"] or "?")]:
    by = defaultdict(lambda: [0, 0])
    for g in dec:
        by[keyf(g)][0] += 1; by[keyf(g)][1] += g["result"] == "WIN"
    print(f"  by {label}:")
    for k, (t, ww) in sorted(by.items()):
        print(f"     {k:13} {ww}/{t} = {ww / t * 100:.0f}%")
