#!/usr/bin/env python
"""Test CLV-conditional strategies on the 72-bet board:
   baseline (bet all straight) vs the user's idea (fade worse-than-close, bet straight on
   beat/flat) vs variants. Fade payout = bet's own odds (1xbet hangs ~flat both sides)."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def settled():
    out = []
    with open(os.path.join(HERE, 'graded_bets.csv'), newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            res = (r.get('result') or '').strip().upper()
            if res.startswith('WIN'):
                r['_win'] = 1; out.append(r)
            elif res in ('LOSS', 'LOSE', 'L'):
                r['_win'] = 0; out.append(r)
    return out


g = settled()


def cb(r):
    v = fnum(r.get('odds_clv'))
    if v is None:
        return 'nodata'
    if v > 1e-9:
        return 'beat'
    if v < -1e-9:
        return 'worse'
    return 'flat'


beat = [r for r in g if cb(r) == 'beat']
flat = [r for r in g if cb(r) == 'flat']
worse = [r for r in g if cb(r) == 'worse']
nodata = [r for r in g if cb(r) == 'nodata']


def straight(items):
    return sum(r['_win'] for r in items), sum(1 - r['_win'] for r in items), sum(fnum(r['pnl']) or 0 for r in items)


def fade(items):
    w = sum(1 - r['_win'] for r in items)
    l = sum(r['_win'] for r in items)
    pnl = sum(((fnum(r['odds']) - 1) if r['_win'] == 0 else -1.0) for r in items)
    return w, l, pnl


def show(name, legs):
    W = L = 0; P = 0.0; nbets = 0
    for w, l, p in legs:
        W += w; L += l; P += p; nbets += w + l
    print(f"  {name:<46} {W:>2}-{L:<2}  ({nbets} bets, {100*W/max(nbets,1):.0f}%)  P&L {P:+.2f}u")


print(f"CLV buckets: beat={len(beat)}  flat={len(flat)}  worse={len(worse)}  nodata={len(nodata)}\n")
show("BASELINE  - bet ALL straight", [straight(g)])
print()
show("Your idea - fade WORSE, straight beat/flat, skip nodata",
     [straight(beat), straight(flat), fade(worse)])
show("  +also fade nodata",
     [straight(beat), straight(flat), fade(worse), fade(nodata)])
print()
show("Skip-not-fade - straight beat/flat, SKIP worse+nodata",
     [straight(beat), straight(flat)])
show("  straight beat/flat, fade worse, SKIP nodata (same as your idea)",
     [straight(beat), straight(flat), fade(worse)])
print()
print("  legs alone:")
print(f"    beat straight : {straight(beat)[0]}-{straight(beat)[1]}  {straight(beat)[2]:+.2f}u")
print(f"    flat straight : {straight(flat)[0]}-{straight(flat)[1]}  {straight(flat)[2]:+.2f}u")
print(f"    worse straight: {straight(worse)[0]}-{straight(worse)[1]}  {straight(worse)[2]:+.2f}u   ->  FADE: {fade(worse)[0]}-{fade(worse)[1]}  {fade(worse)[2]:+.2f}u")
print(f"    nodata straight: {straight(nodata)[0]}-{straight(nodata)[1]}  {straight(nodata)[2]:+.2f}u   ->  FADE: {fade(nodata)[0]}-{fade(nodata)[1]}  {fade(nodata)[2]:+.2f}u")
