# coach_pass.py - the PARKED layers, from plays_text.csv (pbp text re-crawl):
#  1. PASS NETWORK / assisted profile: team assisted-share of makes, alley-oop + dunk + layup (rim
#     service) rates -> offense style; vs opponent's allowed-assisted-rate (pass-defense).
#  2. COACH timeout layer: does the team stop opponent runs after ITS timeouts (needs team nickname map).
#  Features (walk-forward, decayed) -> test vs v5 on margin. stdlib only.
import csv, os, statistics, sys
from collections import defaultdict, deque
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
def f(x):
    try: return float(x)
    except Exception: return 0.0
games = sorted(csv.DictReader(open(os.path.join(D, "games_full.csv"), encoding="utf-8")),
               key=lambda g: (g["date"], g["game_id"]))
p2t = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(D, "box_full.csv"), encoding="utf-8")):
    p2t[r["game_id"]][r["player"]] = r["team"]
# nickname -> abbrev (timeout text is like "Sun Full timeout")
NICK = {"Dream": "ATL", "Sky": "CHI", "Sun": "CON", "Wings": "DAL", "Fever": "IND", "Aces": "LV",
        "Sparks": "LA", "Lynx": "MIN", "Liberty": "NY", "Mercury": "PHX", "Storm": "SEA",
        "Mystics": "WSH", "Valkyries": "GS", "Fire": "POR", "Tempo": "TOR", "Golden State": "GS"}
# per game per team: makes, assisted makes, alley, dunk+layup makes, assisted rim makes
pg = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
tos = defaultdict(list)     # gid -> [(period, team_abbr)]
for r in csv.DictReader(open(os.path.join(D, "plays_text.csv"), encoding="utf-8")):
    gid = r["game_id"]
    if r["kind"] == "timeout":
        txt = r["assister"]     # timeout text stored in assister col
        for nick, ab in NICK.items():
            if txt.startswith(nick):
                tos[gid].append(ab); break
        continue
    tm = p2t.get(gid, {}).get(r["shooter"])
    if not tm or r["made"] != "1": continue
    d = pg[gid][tm]
    d["mk"] += 1
    if r["assister"]: d["ast_mk"] += 1
    if r["alley"] == "1": d["alley"] += 1
    rim = r["layup"] == "1" or r["dunk"] == "1"
    if rim:
        d["rim_mk"] += 1
        if r["assister"]: d["rim_ast"] += 1
DEC = 0.93
astsh = defaultdict(lambda: [0.6, 1.0])     # own assisted share (ball movement)
rimsv = defaultdict(lambda: [0.10, 1.0])    # assisted-rim (cuts/alley-oops SERVED) share of makes
dastsh = defaultdict(lambda: [0.6, 1.0])    # DEFENSE: opp assisted share allowed (pass-defense)
drimsv = defaultdict(lambda: [0.10, 1.0])   # DEFENSE: opp assisted-rim allowed (cut/alley denial)
tor = defaultdict(lambda: [4.0, 1.0])       # timeouts taken per game (coach aggression proxy)
out = {}
season = None
for g in games:
    if g["season"] != season: season = g["season"]
    gid = g["game_id"]; h, a = g["home"], g["away"]
    if not g["home_score"] or gid not in pg: continue
    def gv(d, tm): return d[tm][0] / d[tm][1]
    out[gid] = dict(
        pass_o=gv(astsh, h) - gv(astsh, a),
        rim_sv=gv(rimsv, h) - gv(rimsv, a),
        pass_x=(gv(astsh, h) - (1 - gv(dastsh, a))) - (gv(astsh, a) - (1 - gv(dastsh, h))),
        cut_x=(gv(rimsv, h) * (gv(drimsv, a) / 0.10) - gv(rimsv, a) * (gv(drimsv, h) / 0.10)) * 10,
        tor=gv(tor, h) - gv(tor, a))
    for tm, opp in ((h, a), (a, h)):
        d = pg[gid].get(tm, {})
        mk = d.get("mk", 0)
        if mk > 10:
            for st, key, num in ((astsh, "ast_mk", mk), (rimsv, "rim_ast", mk)):
                s = st[tm]; s[0] = s[0] * DEC + d.get(key, 0) / num; s[1] = s[1] * DEC + 1
            for st, key in ((dastsh, "ast_mk"), (drimsv, "rim_ast")):
                s = st[opp]; s[0] = s[0] * DEC + d.get(key, 0) / mk; s[1] = s[1] * DEC + 1
        nt = sum(1 for t in tos.get(gid, []) if t == tm)
        s = tor[tm]; s[0] = s[0] * DEC + nt; s[1] = s[1] * DEC + 1
rows = list(csv.DictReader(open(os.path.join(D, "feats_v5.csv"), encoding="utf-8")))
NEW = ["pass_o", "rim_sv", "pass_x", "cut_x", "tor"]
cov = sum(1 for r in rows if r["game_id"] in out)
print(f"pbp coverage: {cov}/{len(rows)} games")
for r in rows:
    e = out.get(r["game_id"], {})
    for k in NEW: r[k] = round(e.get(k, 0), 4)
tr = [r for r in rows if r["season"] in ("2023", "2024") and r["game_id"] in out]
te = [r for r in rows if r["season"] in ("2025", "2026") and r["game_id"] in out]
def fit(fs):
    X = [[f(r[k]) for k in fs] + [1] for r in tr]; y = [f(r["margin"]) for r in tr]; k = len(fs) + 1
    XtX = [[sum(X[i][p] * X[i][q] for i in range(len(X))) + (1e-3 if p == q else 0) for q in range(k)] for p in range(k)]
    Xty = [sum(X[i][p] * y[i] for i in range(len(X))) for p in range(k)]
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for c in range(k):
        pv = max(range(c, k), key=lambda r_: abs(M[r_][c])); M[c], M[pv] = M[pv], M[c]
        M[c] = [v / M[c][c] for v in M[c]]
        for r_ in range(k):
            if r_ != c and M[r_][c]: M[r_] = [x2 - M[r_][c] * y2 for x2, y2 in zip(M[r_], M[c])]
    beta = [M[i][k] for i in range(k)]
    Xe = [[f(r[k2]) for k2 in fs] + [1] for r in te]; ye = [f(r["margin"]) for r in te]
    return (statistics.mean(abs(sum(b * x for b, x in zip(beta, xr)) - yv) for xr, yv in zip(Xe, ye)),
            statistics.mean((sum(b * x for b, x in zip(beta, xr)) > 0) == (yv > 0) for xr, yv in zip(Xe, ye)))
V5 = ["pnews", "p3ar", "oreb", "fluid", "drop", "pfr"]
print("v5 (pbp-covered subset):", fit(V5))
for k in NEW: print(f"{k:7} alone:", fit([k]))
for k in NEW: print(f"v5+{k:7}:", fit(V5 + [k]))
