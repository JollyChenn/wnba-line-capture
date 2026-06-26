# fade_strict.py - NO averaging anywhere. For each bet we use the SINGLE other-side scrape
# captured CLOSEST IN TIME to the moment the bet was flagged. The real quote at the real moment.
import csv, datetime
from collections import defaultdict

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def RES(r): return (r.get('result') or '').strip().upper()
def gdate(r):
    s = (r.get('date') or '').strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else s
def parse_ts(s):
    try: return datetime.datetime.fromisoformat((s or '').replace('Z', '+00:00'))
    except Exception: return None

# 1) When was each bet FLAGGED? Pull the FIRST capture timestamp from bets_log per bet key.
opened_ts = {}
try:
    for r in csv.DictReader(open('bets_log.csv', encoding='utf-8')):
        k = (r['player'].lower(), r['market'], r['side'], f(r.get('line')), (r.get('date') or '').strip())
        ts = parse_ts(r.get('captured_utc'))
        if ts and (k not in opened_ts or ts < opened_ts[k]):
            opened_ts[k] = ts
except Exception as e:
    print("bets_log load:", e)
print(f"opening timestamps loaded: {len(opened_ts)} bet keys\n")

# 2) Build the OTHER-side scrape index: every individual (ts, odds) capture preserved (NO median).
comp = defaultdict(list)
for fn in ('xbet_board.csv', 'xbet_snapshots.csv'):
    try:
        for r in csv.DictReader(open(fn, encoding='utf-8')):
            o = f(r.get('odds')); ts = parse_ts(r.get('captured_utc'))
            ln = f(r.get('line'))
            if o and ts and ln is not None:
                comp[(r['player'].lower(), r['market'], r['side'], ln, ts.strftime('%Y-%m-%d'))].append((ts, o))
    except Exception as e:
        print(fn, "load:", e)
print(f"other-side scrape index: {sum(len(v) for v in comp.values())} individual quotes across {len(comp)} keys\n")

# 3) For each graded bet pick the SINGLE closest-in-time other-side quote.
def real_other_at_open(r):
    bd = gdate(r)
    other = 'Over' if r['side'] == 'Under' else 'Under'
    key = (r['player'].lower(), r['market'], other, f(r['line']), bd)
    quotes = comp.get(key, [])
    if not quotes: return None
    target = opened_ts.get((r['player'].lower(), r['market'], r['side'], f(r['line']), bd))
    if target is None:                                     # no bet-open timestamp -> earliest other-side (the open)
        return min(quotes, key=lambda q: q[0])
    return min(quotes, key=lambda q: abs(q[0] - target))   # the real quote at that moment

G = [r for r in csv.DictReader(open('graded_bets.csv', encoding='utf-8')) if RES(r) in ('WIN', 'LOSS')]
print(f"graded: {len(G)}\n")

print("=" * 96)
print("STRICT: each bet uses ONE real scraped other-side quote (closest in time to bet-open). NO averaging.")
print(f"{'signal':12}{'n_total':>8}{'n_priced':>10}{'fade-win%':>11}{'odds_range':>14}{'fade_$':>10}")
by = defaultdict(list)
for r in G: by[r.get('src', '?')].append(r)

def show(label, rows):
    n = len(rows)
    if not n: return
    priced = [(r, real_other_at_open(r)) for r in rows]
    priced = [(r, q) for r, q in priced if q]
    np = len(priced)
    if np == 0:
        print(f"{label:12}{n:>8}{np:>10}{'-':>10} {'-':>14}{'no real odds':>10}")
        return
    odds_list = [q[1] for _, q in priced]
    fwins = sum(1 for r, _ in priced if RES(r) == 'LOSS')
    fwr = 100 * fwins / np
    pnl = sum(((q[1] - 1) if RES(r) == 'LOSS' else -1) for r, q in priced)
    print(f"{label:12}{n:>8}{np:>10}{fwr:>10.0f}% {min(odds_list):.2f}-{max(odds_list):.2f}    {pnl:>+8.2f}u")

for s, rows in sorted(by.items(), key=lambda x: -len(x[1])): show(s, rows)
print("-" * 96); show("ALL", G)

# 4) Show each FTUNDER bet individually so you can see the exact quotes used.
print("\n" + "=" * 96)
print("EVERY FTUNDER bet that has a real same-date Over scrape (the actual prices used, no median):")
print(f"  {'date':10} {'player':20} {'line':>5}  {'bet odds':>9}  {'OTHER@open':>12}  {'result':6}  {'fade':>6}")
for r in by.get('newunder', []):
    q = real_other_at_open(r)
    if not q: continue
    fade_pl = (q[1] - 1) if RES(r) == 'LOSS' else -1
    print(f"  {gdate(r):10} {r['player'][:20]:20} {f(r['line']):>5}  {f(r['odds']):>9.2f}  {q[1]:>12.2f}  {RES(r):6}  {fade_pl:>+6.2f}")
