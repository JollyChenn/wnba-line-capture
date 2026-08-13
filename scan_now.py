# scan_now.py — pull the LIVE 1xbet WNBA board and produce the usual PING format for today's picks:
# player (TEAM) MKT SIDE line@odds [tier - signal - hit% - EV%]. Hit%/EV computed at the ACTUAL 1xbet line.
import csv, sys
import cloud_xbet as c

sys.stdout.reconfigure(encoding="utf-8")
TODAY = "2026-06-16"

PICKS = {}
for r in csv.DictReader(open("picks_log.csv", encoding="utf-8")):
    if r["pick_date"] != TODAY:
        continue
    base = r["market"].split("_")[0]
    side = "Over" if r["market"].endswith("over") else "Under"
    PICKS.setdefault(r["player"].lower(), []).append(
        {"base": base, "side": side, "anchor": float(r["anchor"]), "proj": float(r["proj"]),
         "sd": float(r["sd"] or 2), "sig": r["signals"], "team": r["team"]})

disc = c.get(f"{c.BASE}/LineFeed/Get1x2_VZip?sports=3&champs={c.CHAMP}&count=40&lng=en&mode=4&country=115&getEmpty=true&virtualSports=true")
if not disc:
    print("BLOCKED: 1xbet not reachable (Cloudflare)."); raise SystemExit
games = [e for e in disc.get("Value", []) if isinstance(e, dict) and e.get("O1") and e.get("I")]
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
            pl = o.get("PL"); T = o.get("T")
            if isinstance(pl, dict) and T in c.T2S and o.get("P") is not None and o.get("C"):
                st, sd = c.T2S[T]
                props.setdefault(str(pl.get("N", "")).lower(), {}).setdefault((st, sd), []).append((float(o["P"]), float(o["C"])))
            for x in o.values(): walk(x)
        elif isinstance(o, list):
            for x in o: walk(x)
    walk(val)


def line_for(plow, base, side):
    pp = props.get(plow)
    if not pp or (base, side) not in pp:
        return None
    return (max if side == "Under" else min)(pp[(base, side)], key=lambda t: t[0])


def tier(ph):
    return "STRONG" if ph >= 0.66 else "SOLID" if ph >= 0.58 else "THIN"


bets, paper, overs, skip = [], [], [], []
for plow, picks in PICKS.items():
    for p in picks:
        lo = line_for(plow, p["base"], p["side"])
        if not lo:
            continue
        line, odds = lo
        z = (line - p["proj"]) / max(p["sd"], 1)
        ph = c._ncdf(z) if p["side"] == "Under" else 1 - c._ncdf(z)   # hit% at the ACTUAL 1xbet line
        ev = odds * ph - 1
        team = c._team_ab(p["team"])
        row = (f"• **{plow.title()}** ({team}) {p['base'].upper()} {p['side']} **{line}@{odds}** "
               f"[{tier(ph)} · {p['sig']} · hit {ph*100:.0f}% · EV {ev*100:+.0f}%]")
        is_fwd = any(s in p["sig"] for s in ("ftdrought", "steady", "streak"))
        in_zone = (line >= p["anchor"]) if p["side"] == "Under" else (line <= p["anchor"] + 1)
        if p["side"] == "Over":
            overs.append((ev, row))
        elif not in_zone:
            skip.append((ev, f"{plow.title()} {p['base'].upper()} {line}@{odds} (line<anchor {p['anchor']})"))
        elif is_fwd:
            paper.append((ev, row))
        else:
            bets.append((ev, row))

print("🏀 **1xbet WNBA — live board, today's model picks**  (hit%/EV vs our synthetic line — side-predict, CLV is the proof)\n")
print("✅ **BETS** (proven signal · line in value zone):")
print("\n".join(r for _, r in sorted(bets, reverse=True)) or "  _(none in value zone right now)_")
print("\n🧪 **FORWARD-TEST** (paper — new signals):")
print("\n".join(r for _, r in sorted(paper, reverse=True)) or "  _(none)_")
print("\n⚠️ **HOT-PRA-OVERS** (weak/downgraded signal — skip):")
print("\n".join(r for _, r in sorted(overs, reverse=True)) or "  _(none)_")
print("\n❌ skip (book moved past our median):")
print("  " + " · ".join(s for _, s in sorted(skip, reverse=True)) if skip else "  (none)")
