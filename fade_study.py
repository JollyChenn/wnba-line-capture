# fade_study.py - stdlib-only (no pandas -> no WMI hang). Fresh fade analysis on graded_bets.csv.
# NOTE: the grader writes 'WIN' (upper) for wins, 'loss' (lower) for losses -> normalize case.
# FADE = bet the OTHER side; a fade WINS when the signal's pick LOST.
import csv, statistics, math
from collections import defaultdict

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def RES(r): return (r.get('result') or '').strip().upper()

G = [r for r in csv.DictReader(open('graded_bets.csv', encoding='utf-8')) if RES(r) in ('WIN', 'LOSS')]
nW = sum(1 for r in G if RES(r) == 'WIN'); nL = len(G) - nW
print(f"graded bets: {len(G)}  ({nW} WIN / {nL} loss = {100*nW/len(G):.0f}% as-bet)\n")

# complement (other-side) odds from the two-sided board
comp = defaultdict(list)
try:
    for r in csv.DictReader(open('xbet_board.csv', encoding='utf-8')):
        o = f(r['odds'])
        if o: comp[(r['player'].lower(), r['market'], r['side'], f(r['line']))].append(o)
except Exception as e:
    print("board load:", e)
def fade_odds(r):
    other = 'Over' if r['side'] == 'Under' else 'Under'
    v = comp.get((r['player'].lower(), r['market'], other, f(r['line'])), [])
    return statistics.median(v) if v else None
def z_fade(fwr, n, be=53.5): return (fwr - be) / math.sqrt(be * (100 - be) / n) if n else 0

print("=" * 88)
print("PER-SIGNAL: as-bet record + FADE result  (fade wins when the pick LOST; breakeven fade-win ~53.5%)")
print(f"{'signal':11}{'n':>4}{'bet-win%':>9}{'fade-win%':>10}{'fade-flat':>10}{'fade-REAL(cov)':>15}{'z':>6}")
by = defaultdict(list)
for r in G: by[r.get('src', '?')].append(r)
def line(label, rows):
    n = len(rows)
    if not n: return
    bwr = 100 * sum(1 for r in rows if RES(r) == 'WIN') / n
    fwr = 100 - bwr
    flat = sum((0.87 if RES(r) == 'LOSS' else -1) for r in rows)
    cov = [(r, fade_odds(r)) for r in rows]; cov = [(r, o) for r, o in cov if o]
    real = sum(((o - 1) if RES(r) == 'LOSS' else -1) for r, o in cov)
    realstr = f"{real:+.1f}u({len(cov)})" if cov else "n/a"
    print(f"{label:11}{n:>4}{bwr:>8.0f}%{fwr:>9.0f}%{flat:>+9.1f}u{realstr:>15}{z_fade(fwr,n):>+6.1f}")
for s, rows in sorted(by.items(), key=lambda x: -len(x[1])):
    line(s, rows)
print("-" * 88)
line("ALL", G)

print("\n" + "=" * 88)
print("ODDS-MOVEMENT (CLV) as a fade filter — did the price move AGAINST our pick (bad price)?")
def wr(rows): return 100 * sum(1 for r in rows if RES(r) == 'WIN') / len(rows) if rows else 0
for c in ['sharp_odds_clv', 'odds_clv', 'line_clv']:
    neg = [r for r in G if f(r[c]) is not None and f(r[c]) < 0]
    pos = [r for r in G if f(r[c]) is not None and f(r[c]) > 0]
    print(f"  {c:16} neg-CLV n={len(neg):>3} bet-win%={wr(neg):>3.0f}% -> FADE-win%={100-wr(neg):>3.0f}%  |  pos-CLV n={len(pos):>3} bet-win%={wr(pos):>3.0f}%")
