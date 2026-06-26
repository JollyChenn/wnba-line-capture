# fade_strict.py - NO synthetic odds anywhere. A bet is reported in money ONLY if
# we have the REAL same-date complement price from xbet_board.csv or xbet_snapshots.csv.
# No flat 0.87, no 1.87 average, no inferred-from-vig — if no real other-side scrape exists,
# the bet is DROPPED from the money column.
import csv, statistics
from collections import defaultdict

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def RES(r): return (r.get('result') or '').strip().upper()
def gdate(r):
    s = (r.get('date') or '').strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else s

# --- build SAME-DATE complement table from the two real two-sided sources ---
comp = defaultdict(list)
for fn in ('xbet_board.csv', 'xbet_snapshots.csv'):
    try:
        for r in csv.DictReader(open(fn, encoding='utf-8')):
            o = f(r.get('odds')); d = (r.get('captured_utc') or '')[:10]
            if o and d and f(r.get('line')) is not None:
                comp[(r['player'].lower(), r['market'], r['side'], f(r['line']), d)].append(o)
    except Exception as e:
        print(fn, "load:", e)
print(f"complement table built: {len(comp)} (player,mkt,side,line,date) keys with REAL scraped odds\n")

def real_other_odds(r):
    """Return the REAL median other-side price scraped on the SAME date, or None."""
    other = 'Over' if r['side'] == 'Under' else 'Under'
    v = comp.get((r['player'].lower(), r['market'], other, f(r['line']), gdate(r)), [])
    return statistics.median(v) if v else None

G = [r for r in csv.DictReader(open('graded_bets.csv', encoding='utf-8')) if RES(r) in ('WIN', 'LOSS')]
print(f"total graded: {len(G)}\n")

# strict accounting: split into "has real other-side" vs "no real other-side"
print("=" * 86)
print("STRICT: only count $ on bets where we ACTUALLY scraped the other side at the same date")
print(f"{'signal':12}{'n_total':>8}{'n_with_real':>13}{'fade-win%':>11}{'avg_real_odds':>15}{'fade_$':>10}")
by = defaultdict(list)
for r in G: by[r.get('src', '?')].append(r)
def line(label, rows):
    n = len(rows)
    if not n: return
    with_real = [(r, real_other_odds(r)) for r in rows]
    with_real = [(r, o) for r, o in with_real if o is not None]
    nr = len(with_real)
    fwr_overall = 100 * sum(1 for r in rows if RES(r) == 'LOSS') / n
    if nr == 0:
        print(f"{label:12}{n:>8}{nr:>13}{fwr_overall:>10.0f}%{'-':>15}{'NO REAL ODDS':>10}")
        return
    fwr_real = 100 * sum(1 for r, o in with_real if RES(r) == 'LOSS') / nr
    avgo = statistics.mean(o for _, o in with_real)
    pnl = sum(((o - 1) if RES(r) == 'LOSS' else -1) for r, o in with_real)
    print(f"{label:12}{n:>8}{nr:>13}{fwr_real:>10.0f}%{avgo:>15.2f}{pnl:>+9.2f}u")

for s, rows in sorted(by.items(), key=lambda x: -len(x[1])): line(s, rows)
print("-" * 86); line("ALL", G)

print("\n" + "=" * 86)
print("The fade-win% in this table is computed only on the n_with_real subset")
print("(so it can differ from the all-bets fade-win%). avg_real_odds = actual scraped median.")
print("If n_with_real < ~30, treat the $ figure as anecdotal, not as evidence.")
