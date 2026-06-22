#!/usr/bin/env python
"""
signal_matrix.py - complete performance matrix for the WNBA signal board.
Reads graded_bets.csv (paper signal-tracking, flat 1u) + my_bets.csv (real money).
Pure stdlib (no pandas -> can't hit the WMI import hang). Re-run anytime as data grows.
P&L is at flat 1u vs each bet's captured odds. BE% = break-even win rate at avg odds.
CLV% = mean recorded odds-CLV (count of bets with CLV in parens); >0 = we beat the close.
"""
import csv, os
from collections import defaultdict

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
            r['_win'] = 1
            out.append(r)
        elif res in ('LOSS', 'LOSE', 'L'):
            r['_win'] = 0
            out.append(r)
    return out


def stat(items):
    n = len(items)
    w = sum(r['_win'] for r in items)
    pnl = sum(fnum(r.get('pnl')) or 0 for r in items)
    odds = [fnum(r.get('odds')) for r in items if fnum(r.get('odds'))]
    avgodd = sum(odds) / len(odds) if odds else 0
    clvs = [fnum(r.get('odds_clv')) for r in items if fnum(r.get('odds_clv')) is not None]
    clv = (sum(clvs) / len(clvs) * 100) if clvs else None
    return dict(n=n, w=w, l=n - w, wp=(100 * w / n if n else 0), pnl=pnl,
                upb=(pnl / n if n else 0), odd=avgodd, be=(100 / avgodd if avgodd else 0),
                clv=clv, clvn=len(clvs))


def row_str(label, s):
    wl = f"{s['w']}-{s['l']}"
    clv = f"{s['clv']:+.1f}({s['clvn']})" if s['clv'] is not None else "-"
    flag = "  <-- +EV" if s['wp'] > s['be'] and s['n'] >= 8 else ("  (thin n)" if s['n'] < 8 else "")
    return (f"{str(label):<14}{s['n']:>4}{wl:>8}{s['wp']:>5.0f}%{s['pnl']:>+9.2f}"
            f"{s['upb']:>+8.3f}{s['odd']:>6.2f}{s['be']:>4.0f}%{clv:>10}{flag}")


def table(title, rows, keyfn):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    print(f"\n{'=' * 86}\n {title}\n{'=' * 86}")
    print(f"{'group':<14}{'n':>4}{'W-L':>8}{'win%':>6}{'P&L u':>9}{'u/bet':>8}{'odds':>6}{'BE%':>5}{'CLV%':>10}")
    print('-' * 86)
    data = sorted(((k, stat(v)) for k, v in groups.items()), key=lambda kv: kv[1]['pnl'], reverse=True)
    for k, s in data:
        print(row_str(k, s))
    print('-' * 86)
    print(row_str('TOTAL', stat(rows)))


g = settled(load('graded_bets.csv'))
dates = sorted(r['date'] for r in g)
print(f"WNBA SIGNAL MATRIX  |  {len(g)} settled paper bets  |  {dates[0]} -> {dates[-1]}  |  flat 1u")

table("BY SIGNAL TYPE", g, lambda r: r['src'])
table("BY MARKET / STAT", g, lambda r: r['market'])
table("BY SIDE", g, lambda r: r['side'])
table("BY TIER", g, lambda r: r['tier'])
table("BY SIGNAL x SIDE", g, lambda r: f"{r['src']}/{r['side']}")

# real money
print(f"\n{'=' * 86}\n REAL MONEY PLACED (my_bets.csv)\n{'=' * 86}")
mb = settled(load('my_bets.csv'))
for r in sorted(mb, key=lambda r: r['date']):
    res = 'W' if r['_win'] else 'L'
    print(f"   {r['date']}  {r['player'][:20]:<20} {r['market']:<3} {r['side']:<5} {str(r['line']):>5}  @{str(r['odds']):<5}  {res}  {fnum(r['pnl']) or 0:+.2f}u")
ms = stat(mb)
extra = f"  CLV {ms['clv']:+.1f}%" if ms['clv'] is not None else ""
print(f"   --> {ms['w']}-{ms['l']}  {ms['pnl']:+.2f}u  win {ms['wp']:.0f}%{extra}")

# full per-bet list grouped by signal
print(f"\n{'=' * 86}\n FULL BET LIST (all {len(g)} paper bets, grouped by signal)\n{'=' * 86}")
for src in sorted(set(r['src'] for r in g)):
    items = [r for r in g if r['src'] == src]
    sp = stat(items)
    print(f"\n-- {src}  ({sp['w']}-{sp['l']}, {sp['pnl']:+.2f}u, win {sp['wp']:.0f}%) --")
    for r in sorted(items, key=lambda r: (r['date'], r['player'])):
        res = 'W' if r['_win'] else 'L'
        print(f"   {r['date']}  {r['player'][:20]:<20} {r['market']:<3} {r['side']:<5} {str(r['line']):>5}  @{str(r['odds']):<6} {res} {fnum(r['pnl']) or 0:+.2f}")
