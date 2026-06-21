# check_wheeler.py — pull the LIVE 1xbet board and show whether a player has a line at ANY number (raw, not
# filtered by our signal). Answers "did the line vanish, or just reprice to a number the model stopped flagging?"
import sys, cloud_xbet as c
sys.stdout.reconfigure(encoding="utf-8")
WHO = (sys.argv[1].lower() if len(sys.argv) > 1 else "wheeler")

disc = c.get(f"{c.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={c.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
games = [e for e in (disc or {}).get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
print(f"{len(games)} WNBA game(s) live on the 1xbet board:")
for e in games:
    print(f"  {e.get('O2','?')} @ {e.get('O1','?')}")

props = {}
for e in games:
    mv = c.get(c.gz(e["I"]))
    sg = (mv.get("Value", {}) or {}).get("SG", []) if mv else []
    stat = next((s for s in sg if "stat" in str(s.get("TG", "")).lower()), None)
    if not stat:
        continue
    val = (c.get(c.gz(stat["I"])) or {}).get("Value", {}) or {}
    def walk(o):
        if isinstance(o, dict):
            pl, T = o.get("PL"), o.get("T")
            if isinstance(pl, dict) and T in c.T2S and o.get("P") is not None and o.get("C"):
                st, sd = c.T2S[T]
                props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((st, sd), []).append((float(o["P"]), float(o["C"])))
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(val)

print(f"\n{len(props)} players have props posted.")
hits = [nm for nm in props if WHO in nm]
if hits:
    for nm in hits:
        print(f"\n>>> {nm.title()} IS on the board:")
        for (st, sd), lst in sorted(props[nm].items()):
            print(f"    {st.upper()} {sd}: " + ", ".join(f"{p}@{o}" for p, o in lst))
else:
    print(f"\n>>> '{WHO}' is NOT on the board — no props at any line/odds.")
