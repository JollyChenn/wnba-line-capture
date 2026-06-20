# audit_results.py — INDEPENDENT result check. Re-derives each settled bet's actual straight
# from the box, recomputes WIN/loss/push with an explicit rule, and FLAGS any row where the
# stored graded_bets.csv result disagrees. Read-only. Shows the arithmetic for every bet.
import csv, os
from collections import defaultdict

gd = {r["game_id"]: r.get("date") for r in csv.DictReader(open("data/games_2026.csv", encoding="utf-8"))}
actual = {}
for r in csv.DictReader(open("data/box_2026.csv", encoding="utf-8")):
    d = gd.get(r["game_id"])
    if not d:
        continue
    try:
        p, rb, a = float(r["pts"]), float(r["reb"]), float(r["ast"])
    except (ValueError, TypeError):
        continue
    for mk, v in {"pts": p, "pr": p + rb, "pa": p + a, "ra": rb + a, "pra": p + rb + a}.items():
        actual[(r["player"].lower(), d, mk)] = v             # last write wins if a player had 2 games on a date

rows = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8")))
print(f"auditing {len(rows)} settled bets\n")
print(f"{'date':9}{'player':19}{'bet':16}{'actual':>7}  {'arithmetic':26}{'stored':6} {'check'}")
flags = []
for r in sorted(rows, key=lambda x: (x["date"], x["player"])):
    plow, d, mk, side = r["player"].lower(), r["date"], r["market"], r["side"]
    line = float(r["line"]); stored = r["result"]
    act = actual.get((plow, d, mk))
    if act is None:
        exp, arith = "??NOBOX", "no box row for this game"
    elif act == line:
        exp, arith = "push", f"{act:g} == {line:g}"
    elif (act < line) == (side == "Under"):
        exp, arith = "WIN", f"{act:g} {'<' if side=='Under' else '>'} {line:g} ({side})"
    else:
        exp, arith = "loss", f"{act:g} {'>' if side=='Under' else '<'}= {line:g} ({side} fails)"
    ok = (exp.upper() == stored.upper()) or (exp == "push" and stored == "push")
    mark = "OK" if ok else "  <<< MISMATCH"
    if not ok:
        flags.append((d, r["player"], f"{mk.upper()} {side} {line:g}", act, stored, exp))
    actstr = "—" if act is None else f"{act:g}"
    print(f"{d:9}{r['player'][:18]:19}{(mk.upper()+' '+side+' '+f'{line:g}')[:15]:16}{actstr:>7}  {arith:26}{stored:6} {mark}")

print()
if flags:
    print(f"!!! {len(flags)} MIS-GRADED ROW(S) FOUND:")
    for d, pl, bet, act, stored, exp in flags:
        print(f"   {d} {pl} {bet}: actual={act} -> should be {exp.upper()}, but stored '{stored}'")
else:
    print("✅ ALL SETTLED BETS GRADED CORRECTLY — every stored WIN/loss/push matches the box arithmetic.")
