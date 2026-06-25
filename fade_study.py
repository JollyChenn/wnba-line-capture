# fade_study.py - stdlib-only. Fade analysis with DATE-MATCHED complement odds (the correct way).
# The complement (other-side) price MUST come from the SAME date as the bet - never today's board.
# Sources for the other side: xbet_board.csv (both sides, but only since 06-24) + xbet_snapshots.csv
# (full period, but captured mostly the bet side) - so TRUE coverage is honest/low for old bets.
import csv, statistics, math
from collections import defaultdict

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def RES(r): return (r.get('result') or '').strip().upper()
def gdate(r):                                   # graded "20260614" -> "2026-06-14"
    s = (r.get('date') or '').strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else s

G = [r for r in csv.DictReader(open('graded_bets.csv', encoding='utf-8')) if RES(r) in ('WIN', 'LOSS')]
nW = sum(1 for r in G if RES(r) == 'WIN')
print(f"graded bets: {len(G)}  ({nW} WIN / {len(G)-nW} loss = {100*nW/len(G):.0f}% as-bet)\n")

# complement odds keyed WITH DATE, from both two-sided sources
comp = defaultdict(list)
for fn in ('xbet_board.csv', 'xbet_snapshots.csv'):
    try:
        for r in csv.DictReader(open(fn, encoding='utf-8')):
            o = f(r['odds']); d = (r.get('captured_utc') or '')[:10]
            if o: comp[(r['player'].lower(), r['market'], r['side'], f(r['line']), d)].append(o)
    except Exception as e:
        print(fn, "load:", e)
def fade_odds(r):                               # OTHER side, SAME date
    other = 'Over' if r['side'] == 'Under' else 'Under'
    v = comp.get((r['player'].lower(), r['market'], other, f(r['line']), gdate(r)), [])
    return statistics.median(v) if v else None

# honest coverage report
recent = [r for r in G if gdate(r) >= '2026-06-24']
old = [r for r in G if gdate(r) < '2026-06-24']
print("TRUE same-date complement-odds coverage:")
print(f"  overall: {sum(1 for r in G if fade_odds(r))}/{len(G)}")
print(f"  recent (>=06-24, board exists): {sum(1 for r in recent if fade_odds(r))}/{len(recent)}")
print(f"  older  (<06-24, no board):      {sum(1 for r in old if fade_odds(r))}/{len(old)}")

print("\n" + "=" * 80)
print("FADE with PROPER same-date complement (fade-win% valid for all; $ only where covered)")
print(f"{'signal':11}{'n':>4}{'bet-win%':>9}{'fade-win%':>10}{'fade$ @real(cov)':>18}")
by = defaultdict(list)
for r in G: by[r.get('src', '?')].append(r)
def line(label, rows):
    n = len(rows)
    if not n: return
    bwr = 100 * sum(1 for r in rows if RES(r) == 'WIN') / n
    cov = [(r, fade_odds(r)) for r in rows]; cov = [(r, o) for r, o in cov if o]
    real = sum(((o - 1) if RES(r) == 'LOSS' else -1) for r, o in cov)
    realstr = f"{real:+.1f}u({len(cov)}/{n})" if cov else f"n/a(0/{n})"
    print(f"{label:11}{n:>4}{bwr:>8.0f}%{100-bwr:>9.0f}%{realstr:>18}")
for s, rows in sorted(by.items(), key=lambda x: -len(x[1])): line(s, rows)
print("-" * 80); line("ALL", G)
