# void_dnp.py - settle bets on players who never took the floor.
# ---------------------------------------------------------------------------------------------
# A late scratch leaves a bet in limbo. The graders key on (slate, player) in the box score, so a
# DNP never matches and the row sits "pending" forever - indistinguishable from a game that has
# not been played yet. DeWanna Bonner 2026-08-25 was the case that surfaced it: the injury guard
# passed her, she was scratched after the card went out, WSH@PHX finished, and her row stayed open.
#
# A book VOIDS these and returns the stake, so the right treatment is a third outcome - not a win,
# not a loss, and NOT counted in n. That is already how the ROI code behaves toward an unsettled
# row, so this changes no number; what it changes is that the row is visibly resolved instead of
# masquerading as grading lag, and it can never later be miscounted as a loss.
#
# SAFETY: only void when the game is final AND the box holds OTHER players from that same game.
# Without that second test a slow box fetch would be indistinguishable from a scratch, and we
# would void bets that are merely waiting for data.
import csv, os, shutil, sys, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))

gmeta, final_dates = {}, set()
for g in csv.DictReader(open(os.path.join(D, "data", "games_2026.csv"), encoding="utf-8")):
    gmeta[g["game_id"]] = (g.get("date", ""), (g.get("home_score") or "").strip() != "")
    if (g.get("home_score") or "").strip(): final_dates.add(g.get("date", ""))

played_by_date = collections.defaultdict(set)     # date -> players with a box row
box_games_by_date = collections.defaultdict(set)  # date -> game_ids the box actually covers
for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8")):
    d, fin = gmeta.get(r["game_id"], ("", False))
    if not d: continue
    played_by_date[d].add((r.get("player") or "").lower())
    box_games_by_date[d].add(r["game_id"])

# a date is safe to void against only if every FINAL game on it has box rows
safe = set()
for d in final_dates:
    want = {gid for gid, (dd, fin) in gmeta.items() if dd == d and fin}
    if want and want <= box_games_by_date.get(d, set()): safe.add(d)

for name in ("model_forward.csv", "shadow_forward.csv"):
    path = os.path.join(D, name)
    if not os.path.exists(path): continue
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows: continue
    n = 0
    for r in rows:
        if (r.get("result") or "").strip(): continue
        sl = (r.get("slate") or "").replace("-", "")
        if sl not in safe: continue
        if (r.get("player") or "").lower() in played_by_date.get(sl, set()): continue
        r["result"] = "void"
        r["actual"] = ""
        note = r.get("note")
        if note is not None: r["note"] = "DNP - stake returned"
        n += 1
        print(f"  VOID {sl} {r.get('player'):<22} {(r.get('market') or '').upper():<4} "
              f"{r.get('config', 'LIVE')}")
    if not n:
        print(f"  {name}: nothing to void"); continue
    bak = path.replace(".csv", ".pre-void.bak.csv")
    if not os.path.exists(bak): shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)                          # atomic
    print(f"  {name}: voided {n} row(s), backup {os.path.basename(bak)}")
