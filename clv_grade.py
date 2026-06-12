# ============================================================================
# clv_grade.py — PAPER CLV on the model's picks (no real bets required)
# ============================================================================
# Answers "what CLV are we measuring if we don't bet anything?":
#   For every pick the model made (picks_log.csv), we look up Pinnacle's line for
#   that player at the FIRST capture (open) and LAST capture (close) in
#   line_snapshots.csv. The question is simply: did the market move TOWARD our
#   under by close? If our 'under' picks see the line drop / the under price
#   shorten, our signal LED the sharp market = real edge — proven with zero money
#   at risk. This is the validation gate before betting real size.
#
# Markets we can grade = those the-odds-api captures (points, PRA). PR/PA/RA are
# 1xbet-only combos the-odds-api doesn't post, so they aren't CLV-graded here.
#
# Run:  python clv_grade.py
# ============================================================================
import os, sys
import pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

PICKS = "picks_log.csv"
SNAPS = "line_snapshots.csv"
MAP = {"pts_under": "player_points", "pra_under": "player_points_rebounds_assists"}

if not os.path.exists(PICKS):
    print("No picks_log.csv yet."); sys.exit()
picks = pd.read_csv(PICKS, dtype=str)
picks = picks[picks.market.isin(MAP)]
if not os.path.exists(SNAPS):
    print("=" * 78)
    print("CLV GRADER READY — but no line_snapshots.csv captured yet.")
    print("=" * 78)
    print("What it will measure once the hourly capture has logged Pinnacle lines:")
    print("  • for each pick, Pinnacle's OPEN vs CLOSE line + under price")
    print("  • did the line drop / under shorten by close = market moved TO our under (+CLV)")
    print("  • % of picks with +CLV  →  our signal leads the sharp line = real edge")
    print(f"\n{len(picks)} gradeable picks (points/PRA) waiting. Capture runs near tip; check back after games.")
    sys.exit()

snaps = pd.read_csv(SNAPS, dtype=str)
snaps = snaps[snaps.side.str.lower() == "under"].copy()
snaps["captured_utc"] = pd.to_datetime(snaps["captured_utc"], errors="coerce")
snaps["line"] = pd.to_numeric(snaps["line"], errors="coerce")
snaps["price"] = pd.to_numeric(snaps["price"], errors="coerce")
snaps = snaps[snaps.book.str.contains("pinnacle", case=False, na=False)]

rows = []
for _, p in picks.iterrows():
    mk = MAP[p.market]
    s = snaps[(snaps.player == p.player) & (snaps.market == mk)].sort_values("captured_utc")
    if len(s) < 1:
        continue
    op, cl = s.iloc[0], s.iloc[-1]
    proj = float(p.proj) if p.get("proj") not in (None, "", "nan") else float("nan")
    line_drift = op.line - cl.line              # + => line dropped toward under (good)
    price_drift = op.price - cl.price           # + => under price shortened (more favored = good)
    clv_pos = (line_drift > 0) or (price_drift > 0.01)
    rows.append({
        "player": p.player, "market": p.market, "proj": proj,
        "open": f"{op.line}@{op.price}", "close": f"{cl.line}@{cl.price}",
        "line_drift": round(line_drift, 1), "price_drift": round(price_drift, 3),
        "close_vs_proj": round(cl.line - proj, 1) if proj == proj else None,
        "CLV": "+" if clv_pos else "-",
    })

print("=" * 90)
print("PAPER CLV — model picks vs Pinnacle open->close (no real bets)")
print("=" * 90)
if not rows:
    print(f"{len(picks)} gradeable picks, but none matched a captured Pinnacle line yet.")
    print("(Props post near tip; the hourly capture will fill this in once games approach.)")
    sys.exit()
d = pd.DataFrame(rows)
for _, r in d.iterrows():
    print(f"  {r.player[:20]:<20} {r.market:<10} proj {r.proj:<5} | open {r['open']:>10} -> close {r['close']:>10} "
          f"| drift {r.line_drift:+.1f}pt {r.price_drift:+.2f}  CLV {r.CLV}")
pct = (d.CLV == "+").mean() * 100
print("-" * 90)
print(f"  graded {len(d)} picks | +CLV {pct:.0f}% | avg line drift {d.line_drift.mean():+.2f}pt "
      f"| avg price drift {d.price_drift.mean():+.3f}")
print(f"  READ: >55% +CLV (and positive avg drift) = our picks lead Pinnacle's close = REAL EDGE.")
print(f"  <50% = the sharp market moves AGAINST us = edge not there. Need ~2 weeks for signal.")
print("=" * 90)
