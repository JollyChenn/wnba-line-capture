# purge_allstar.py - remove the All-Star exhibition rows the old season-type filter let through.
# ---------------------------------------------------------------------------------------------
# ESPN reports 2026-07-25 COOP v SPO as type=2 / slug=regular-season, so daily_picks' old
# `type != 2 -> skip` test never blocked it and 22 exhibition box rows entered the cache. Those
# rows are what poisoned trailing medians: Allisha Gray read 24.0 unfiltered against 26.0 on
# ATL-only games, which moved her across the cushion-3 boundary and briefly manufactured a
# "finding" that did not exist.
#
# The cache is append-only (concat + drop_duplicates), so fixing the filter stops the rows coming
# back but does not remove the ones already stored. This deletes them once. Safe to re-run: if
# they are already gone it reports zero removed and rewrites nothing.
#
# Backups are written first, and each file is replaced atomically.
import csv, os, shutil, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
BAD = {"401857320"}                      # 2026-07-25 COOP v SPO
FRANCHISES = {"ATL","CHI","CON","DAL","GS","IND","LA","LV","MIN","NY","PHX","POR","SEA","TOR","WSH"}

games_p = os.path.join(D, "data", "games_2026.csv")
box_p = os.path.join(D, "data", "box_2026.csv")
# widen BAD to any game involving a non-franchise side, so a future exhibition is caught too
for r in csv.DictReader(open(games_p, encoding="utf-8")):
    if r.get("home") not in FRANCHISES or r.get("away") not in FRANCHISES:
        BAD.add(r.get("game_id"))
print("exhibition game_ids to purge:", sorted(BAD))
for path in (box_p, games_p):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows: print(f"  {os.path.basename(path)}: empty, skipped"); continue
    keep = [r for r in rows if r.get("game_id") not in BAD]
    if len(keep) == len(rows):
        print(f"  {os.path.basename(path)}: nothing to remove ({len(rows)} rows)"); continue
    bak = path.replace(".csv", ".pre-allstar-purge.bak.csv")
    if not os.path.exists(bak): shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(keep)
    os.replace(tmp, path)                # atomic - never a half-written data file
    print(f"  {os.path.basename(path)}: {len(rows)} -> {len(keep)}  (removed {len(rows)-len(keep)}, backup {os.path.basename(bak)})")
