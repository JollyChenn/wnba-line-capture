#!/usr/bin/env python
"""(1) Does FADING book-overshoot overs beat betting them, and where is the trap?
   (2) Does odds movement (CLV) sort winners from losers? Pure stdlib."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(name):
    with open(os.path.join(HERE, name), newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def settled(rows):
    out = []
    for r in rows:
        res = (r.get('result') or '').strip().upper()
        if res.startswith('WIN'):
            r['_win'] = 1; out.append(r)
        elif res in ('LOSS', 'LOSE', 'L'):
            r['_win'] = 0; out.append(r)
    return out


def rec(items):
    n = len(items); w = sum(r['_win'] for r in items)
    pnl = sum(fnum(r['pnl']) or 0 for r in items)
    return n, w, n - w, (100 * w / n if n else 0), pnl


def fade_pnl(items):
    # fade wins when the over LOST; payout at the bet's own odds (1xbet hangs ~flat both sides)
    return sum(((fnum(r['odds']) - 1) if r['_win'] == 0 else -1.0) for r in items)


g = settled(load('graded_bets.csv'))

print("=" * 72)
print(" PART 1  -  BOOK OVERSHOOT:  bet it  vs  FADE it")
print("=" * 72)
ov = [r for r in g if r['src'] == 'overshoot']
n, w, l, wp, pnl = rec(ov)
print(f"\n  BET THE OVER (what the bot does):  {w}-{l}  win {wp:.0f}%  P&L {pnl:+.2f}u")
fw = l
print(f"  FADE IT (take the UNDER):          {fw}-{w}  win {100*fw/n:.0f}%  P&L {fade_pnl(ov):+.2f}u")
print(f"  (fade payout = each bet's own odds; 1xbet hangs ~flat both sides, so realistic)")
print("\n  WHERE'S THE TRAP?  by line size:")
print(f"   {'bucket':<16}{'n':>3}  {'over rec':>9}{'over P&L':>10}   {'fade rec':>9}{'fade P&L':>10}")
for lab, test in [("big line >=18", lambda r: fnum(r['line']) >= 18),
                  ("small line <18", lambda r: fnum(r['line']) < 18)]:
    sub = [r for r in ov if test(r)]
    if not sub:
        continue
    n, w, l, wp, pnl = rec(sub)
    print(f"   {lab:<16}{n:>3}  {f'{w}-{l}':>9}{pnl:>+10.2f}   {f'{l}-{w}':>9}{fade_pnl(sub):>+10.2f}")
print("\n  WHERE'S THE TRAP?  by market:")
mk = {}
for r in ov:
    mk.setdefault(r['market'], []).append(r)
for m, sub in sorted(mk.items()):
    n, w, l, wp, pnl = rec(sub)
    print(f"   {m:<16}{n:>3}  {f'{w}-{l}':>9}{pnl:>+10.2f}   {f'{l}-{w}':>9}{fade_pnl(sub):>+10.2f}")

print("\n" + "=" * 72)
print(" PART 2  -  ODDS MOVEMENT (CLV):  does the line moving our way create winners?")
print("=" * 72)


def buckets(col):
    b = {'beat close (CLV>0)': [], 'flat (CLV=0)': [], 'worse close (CLV<0)': [], 'no data': []}
    for r in g:
        v = fnum(r.get(col))
        if v is None:
            b['no data'].append(r)
        elif v > 1e-9:
            b['beat close (CLV>0)'].append(r)
        elif v < -1e-9:
            b['worse close (CLV<0)'].append(r)
        else:
            b['flat (CLV=0)'].append(r)
    return b


for col, label in [('odds_clv', 'ODDS-CLV  (our price vs the close)'),
                   ('line_clv', 'LINE-CLV  (the prop line moved)')]:
    print(f"\n  {label}:")
    print(f"   {'bucket':<22}{'n':>4}{'W-L':>8}{'win%':>6}{'P&L u':>9}")
    for k, items in buckets(col).items():
        if not items:
            continue
        n, w, l, wp, pnl = rec(items)
        print(f"   {k:<22}{n:>4}{f'{w}-{l}':>8}{wp:>5.0f}%{pnl:>+9.2f}")
