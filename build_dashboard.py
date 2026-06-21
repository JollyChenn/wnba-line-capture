# -*- coding: utf-8 -*-
"""
build_dashboard.py — clean two-section dashboard.html from the bot's CSVs.
No external libs. Re-run anytime (the grade-bets workflow runs it on cron).

Two sections, nothing else:
  💰 REAL MONEY  = COLD/SHRINK/STINGY only (src=model) — the only real-money signal.
  🧪 PAPER TESTING = every other signal, merged into ONE bucket.
Each section: pending (unsettled) at top, then settled marked WIN/LOSE, flat 1u stake P&L.
"""
import csv, os, html, datetime
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(ROOT, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []

graded   = load("graded_bets.csv")
bets_log = load("bets_log.csv")
mybets   = load("my_bets.csv")
esc = lambda s: html.escape(str(s))

# player -> most-recent team (data files don't store team; the box does). Shown next to each name on the board.
_gdate = {r.get("game_id"): r.get("date", "") for r in load("data/games_2026.csv")}
_team_by = {}
for _r in load("data/box_2026.csv"):
    _pl, _tm = (_r.get("player") or "").lower(), (_r.get("team") or "")
    _d = _gdate.get(_r.get("game_id"), "")
    if _pl and _tm and (_pl not in _team_by or _d >= _team_by[_pl][0]):
        _team_by[_pl] = (_d, _tm)                       # keep the LATEST team (handles mid-season moves)
TEAM_FULL = {                                          # ESPN abbreviation -> full WNBA team name (incl. 2026 expansion)
    "ATL": "Atlanta Dream", "CHI": "Chicago Sky", "CON": "Connecticut Sun", "DAL": "Dallas Wings",
    "GS": "Golden State Valkyries", "IND": "Indiana Fever", "LA": "Los Angeles Sparks", "LV": "Las Vegas Aces",
    "MIN": "Minnesota Lynx", "NY": "New York Liberty", "PHX": "Phoenix Mercury", "POR": "Portland Fire",
    "SEA": "Seattle Storm", "TOR": "Toronto Tempo", "WSH": "Washington Mystics",
}
def team_of(name):                                     # -> just the nickname (Dream / Sparks / Lynx); falls back to the abbreviation
    ab = _team_by.get((name or "").lower(), ("", ""))[1]
    full = TEAM_FULL.get(ab, ab)
    return full.split()[-1] if full else ""            # last word = the nickname (all WNBA nicknames are one word)

REAL_SRC = {"model"}                                   # COLD/SHRINK/STINGY = the ONLY real-money signal
SIG_NAME = {                                           # proper display names (internal keys stable)
    "model": "COLD/SHRINK/STINGY", "flip": "FLIP UNDER", "flip_paper": "FLIP UNDER",
    "newunder": "FTUNDER", "hotover": "HOT OVER", "usgshock": "usgshock",
    "cascade": "STAR-OUT CASCADE", "starout": "starout", "overshoot": "BOOK OVERSHOOT", "fragile": "fragile",
}
def signame(s): return SIG_NAME.get(s, s or "?")
def srcof(r):  return r.get("src") or ("model" if r.get("side") == "Under" else "overshoot")
def is_real(s): return s in REAL_SRC

# ---- settled: REAL MONEY = the bets YOU actually placed (my_bets); PAPER = bot's non-model graded ----
settled_real  = mybets                                  # your actual real-money bets (the line/result you took)
settled_paper = [r for r in graded if not is_real(srcof(r))]
signal_model  = [r for r in graded if is_real(srcof(r))]   # bot's COLD/SHRINK/STINGY at take-on-sight — for the CLV PROOF note only

# ---- PENDING -------------------------------------------------------------------------------------------------
# REAL-MONEY (model) bets must NEVER silently drop off the board. A model bet captured a day+ before its game
# (under an EARLIER LA slate) used to vanish the moment the slate rolled. Now: show EVERY un-settled model bet from
# the last ~3 slates (the 48h capture window), newest capture per player+market, with a "last seen" freshness so a
# line that got PULLED (stale) is flagged instead of disappearing. PAPER stays latest-slate only (it's high-volume).
_model_caps = [r.get("captured_utc","") for r in bets_log if is_real(r.get("src","")) and r.get("captured_utc")]
_latest_model = max(_model_caps) if _model_caps else ""   # newest time the LAPTOP actually scanned for real-money bets
def _stale_line(ts):                                       # True = line likely PULLED: a newer model scan didn't re-capture this bet
    if not _latest_model or not ts:
        return False
    try:
        return (datetime.datetime.fromisoformat(_latest_model.replace("Z", "+00:00"))
                - datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))).total_seconds() > 1800  # >30 min newer scan, no re-capture
    except Exception:
        return False
_slates = sorted({r.get("date","") for r in bets_log if r.get("date","")})
_latest = _slates[-1] if _slates else ""
_recent = set(_slates[-3:])                             # real-money visibility window (~48h: captured days before tip)
settled_keys = {(r.get("date","").replace("-",""), r.get("player","").lower(), r.get("market","")) for r in graded}
mb_players = {r.get("player","").lower() for r in mybets}
seen_r, seen_p, pending_real, pending_paper = set(), set(), [], []
for r in reversed(bets_log):                            # newest capture per player+market wins (bets_log is append-order)
    p = r.get("player","")
    if not p:
        continue
    k = (r.get("date","").replace("-",""), p.lower(), r.get("market",""))
    if k in settled_keys:
        continue
    if is_real(r.get("src","")):                        # REAL MONEY: last ~3 slates, exclude what you already placed
        if r.get("date","") in _recent and k not in seen_r and p.lower() not in mb_players:
            seen_r.add(k); r["_stale"] = _stale_line(r.get("captured_utc","")); pending_real.append(r)
    elif r.get("date","") == _latest and k not in seen_p:   # PAPER: latest slate only
        seen_p.add(k); pending_paper.append(r)
pending_real.sort(key=lambda r: r.get("player",""))
pending_paper.sort(key=lambda r: r.get("player",""))

# ---- per-section summary (flat 1u stake) -----------------------------------
def _nums(settled, col):
    out = []
    for r in settled:
        v = r.get(col)
        if v in ("", "None", None):
            continue
        try: out.append(float(v))
        except ValueError: pass
    return out

def summarize(settled):
    w = sum(1 for r in settled if r.get("result") == "WIN")
    l = sum(1 for r in settled if r.get("result") in ("loss", "LOSS"))
    pnl = sum(float(r.get("pnl") or 0) for r in settled)
    clv = _nums(settled, "odds_clv")                   # self odds-CLV (1xbet's own close — weak)
    slc = _nums(settled, "sharp_clv")                  # line vs Pinnacle (pts; combos incl.)
    soc = _nums(settled, "sharp_odds_clv")             # price vs Pinnacle's fair price (TRUE edge test)
    n = w + l
    avg = lambda xs: (sum(xs)/len(xs) if xs else None)
    return dict(w=w, l=l, n=n, hit=(w/n if n else None), pnl=pnl,
                clv=avg(clv), nclv=len(clv), slc=avg(slc), nslc=len(slc), soc=avg(soc), nsoc=len(soc))

rs, ps = summarize(settled_real), summarize(settled_paper)
sig = summarize(signal_model)                          # signal CLV proof (take-on-sight, separate from your actual P&L)
BE = 0.556

# ---- formatting helpers ----------------------------------------------------
def pct(x):  return "—" if x is None else f"{x*100:.0f}%"
def clvfmt(x): return "—" if x is None else f"{x*100:+.1f}%"
def ptsfmt(x): return "—" if x is None else f"{x:+.2f} pts"
def sig_clv_html(s):                                   # the three CLVs side by side: sharp-odds (true test) > sharp-line > self
    return (f'★ <b>sharp-odds</b> {clvfmt(s["soc"])} <span class="muted">(n={s["nsoc"]}, vs Pinnacle fair price — TRUE edge)</span> · '
            f'<b>sharp-line</b> {ptsfmt(s["slc"])} <span class="muted">(n={s["nslc"]})</span> · '
            f'<b>self</b> {clvfmt(s["clv"])} <span class="muted">(n={s["nclv"]}, 1xbet close — weak)</span>')
def betname(r): return f'{r.get("market","").upper()} {r.get("side","")} {r.get("line","")}'
def player_cell(r):                                    # player name + their team (muted) next to it
    tm = team_of(r.get("player", ""))
    tag = f' <span class="mut" style="font-size:12px">{esc(tm)}</span>' if tm else ''
    return f'<td><b>{esc(r.get("player",""))}</b>{tag}</td>'
def logged_cell(r):                                    # WHEN this bet was first captured (transparency) -> MM-DD
    d = r.get("opened") or (r.get("captured_utc", "") or "")[:10]   # settled: first-capture date; pending: capture date
    if not d:                                          # my_bets (hand-entered) -> fall back to the bet date
        dt = r.get("date", "")
        d = f"{dt[4:6]}-{dt[6:8]}" if len(dt) == 8 else dt
    else:
        d = d[5:] if len(d) >= 10 else d
    return f'<td class="mut" style="font-size:12px">{esc(d)}</td>'
def resfmt(res):
    if res == "WIN": return ('✅ WIN', 'pos')
    if res in ("loss", "LOSS"): return ('❌ LOSE', 'neg')
    if res == "push": return ('➖ push', 'muted')
    return ('· · ·', 'muted')

# build the combined rows for a section: pending first (⏳), then settled newest-first
def section_rows(pend, settled, with_sig):
    out = []
    for r in pend:
        sig = f'<td>{esc(signame(r.get("src","")))}</td>' if with_sig else ''
        plbl, pcls = ('⚠ line pulled', 'pill neg') if r.get("_stale") else ('⏳ pending', 'pill')
        out.append(f'<tr class="pend"><td>{esc(r.get("date",""))}</td>{player_cell(r)}{logged_cell(r)}'
                   f'<td>{esc(betname(r))} @ {esc(r.get("odds",""))}</td>{sig}'
                   f'<td><span class="{pcls}">{esc(plbl)}</span></td><td class="muted">—</td><td class="muted">—</td></tr>')
    for r in sorted(settled, key=lambda x: x.get("date",""), reverse=True):
        txt, cl = resfmt(r.get("result",""))
        try: pnl = float(r.get("pnl") or 0)
        except ValueError: pnl = 0.0
        oc = r.get("odds_clv","")
        try: ocf = clvfmt(float(oc)) if oc not in ("","None",None) else "—"
        except ValueError: ocf = "—"
        sig = f'<td>{esc(signame(srcof(r)))}</td>' if with_sig else ''
        out.append(f'<tr><td>{esc(r.get("date",""))}</td>{player_cell(r)}{logged_cell(r)}'
                   f'<td>{esc(betname(r))} @ {esc(r.get("odds",""))}</td>{sig}'
                   f'<td class="{cl}">{txt}</td><td class="{"pos" if pnl>0 else ("neg" if pnl<0 else "muted")}">{pnl:+.2f}u</td>'
                   f'<td class="{("pos" if (oc not in ("","None",None) and float(oc or 0)>0) else "muted")}">{ocf}</td></tr>')
    if not out:
        cols = 8 if with_sig else 7
        out.append(f'<tr><td colspan="{cols}" class="empty">— none yet —</td></tr>')
    return "".join(out)

real_rows  = section_rows(pending_real,  settled_real,  with_sig=False)
paper_rows = section_rows(pending_paper, settled_paper, with_sig=True)

def summ_line(s, kind):
    rec = f'{s["w"]}–{s["l"]}'
    hit = pct(s["hit"]); pnl = f'{s["pnl"]:+.2f}u'; clv = clvfmt(s["clv"])
    pcls = "pos" if s["pnl"] > 0 else ("neg" if s["pnl"] < 0 else "muted")
    ccls = "pos" if (s["clv"] or 0) > 0 else ("neg" if (s["clv"] or 0) < 0 else "muted")
    return (f'<div class="summ"><span><b>{rec}</b> ({hit} hit)</span>'
            f'<span>P&amp;L <b class="{pcls}">{pnl}</b> <span class="muted">flat 1u</span></span>'
            f'<span>CLV <b class="{ccls}">{clv}</b> <span class="muted">n={s["nclv"]}</span></span>'
            f'<span class="muted">{len(pending_real if kind=="real" else pending_paper)} pending · {s["n"]} settled</span></div>')

# ---- per-signal scoreboard: W-L, P&L, CLV for EACH model (take-on-sight, flat 1u) — compact, no scrolling ----
def scoreboard_html():
    agg = defaultdict(lambda: {"w": 0, "l": 0, "pnl": 0.0, "clv": [], "pend": 0})
    for r in graded:                                   # every graded bet (model + all paper signals)
        a = agg[signame(srcof(r))]
        res = r.get("result", "")
        if res == "WIN": a["w"] += 1
        elif res in ("loss", "LOSS"): a["l"] += 1
        a["pnl"] += float(r.get("pnl") or 0)
        oc = r.get("odds_clv")
        if oc not in ("", "None", None):
            try: a["clv"].append(float(oc))
            except ValueError: pass
    for r in (pending_real + pending_paper):           # tonight's not-yet-settled, per signal
        agg[signame(r.get("src", ""))]["pend"] += 1
    out = []
    for nm, a in sorted(agg.items(), key=lambda kv: (kv[1]["w"] + kv[1]["l"] == 0, -kv[1]["pnl"])):
        n = a["w"] + a["l"]
        hit = f'{a["w"] / n * 100:.0f}%' if n else "—"
        clv = clvfmt(sum(a["clv"]) / len(a["clv"])) if a["clv"] else "—"
        pcls = "pos" if a["pnl"] > 0 else ("neg" if a["pnl"] < 0 else "muted")
        real = ' <span class="pill">💰 real</span>' if nm == "COLD/SHRINK/STINGY" else ''
        out.append(f'<tr><td><b>{esc(nm)}</b>{real}</td><td><b>{a["w"]}–{a["l"]}</b></td><td class="muted">{hit}</td>'
                   f'<td class="{pcls}"><b>{a["pnl"]:+.2f}u</b></td><td class="muted">{clv}</td>'
                   f'<td class="muted">{a["pend"] or "—"}</td></tr>')
    return "".join(out) or '<tr><td colspan="6" class="empty">— none yet —</td></tr>'

gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
through = max((r.get("date","") for r in graded), default="—")
slate = max((r.get("date","") for r in bets_log), default="—")
clvhead = (clvfmt(rs["clv"]) + (" (negative)" if (rs["clv"] or 0) < 0 else "")) if rs["clv"] is not None else "not measured yet"

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WNBA prop bot — dashboard</title><style>
*{box-sizing:border-box} body{margin:0;background:#0d1020;color:#e8ecff;
font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:16px;margin:30px 0 6px;display:flex;align-items:center;gap:8px}
.sub2{color:#7e87b8;font-size:13px}
.banner{background:#1a1430;border:1px solid #5b4b8a;border-radius:12px;padding:12px 16px;margin:16px 0;color:#ffd9a8}
.banner b{color:#ffb86b}
.summ{display:flex;flex-wrap:wrap;gap:18px;background:#151a31;border:1px solid #262d4f;border-radius:10px;
padding:10px 16px;margin:4px 0 10px;font-size:14px}
table{width:100%;border-collapse:collapse;background:#151a31;border:1px solid #262d4f;border-radius:12px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #20264433} td{font-size:14px}
th{color:#8b93c2;font-size:12px;text-transform:uppercase;letter-spacing:.04em;background:#11152a}
tr:nth-child(even) td{background:#12172c} tr.pend td{background:#1a1f3a}
.pos{color:#3fb950} .neg{color:#f85149} .muted,.mut{color:#7e87b8}
.pill{font-size:11px;padding:2px 8px;border-radius:20px;background:#2a3358;color:#aeb6e0}
.empty{color:#7e87b8;padding:10px 0;text-align:center} .foot{color:#5a628f;font-size:12px;margin-top:28px}
.real h2{color:#5fd07a} .paper h2{color:#aeb6e0}
</style></head><body><div class="wrap">
<h1>🏀 WNBA prop bot</h1><div class="sub2">latest slate __SLATE__ · settled through __THROUGH__ · generated __GEN__</div>
<div class="banner">⚠️ <b>UNPROVEN — paper / tiny stakes only.</b> Every line is vs a synthetic median (predicts the SIDE, not that it beats the book). <b>CLV is the only proof</b> — real-money CLV is __CLVHEAD__ so far. Never auto-bet.</div>

<h2>📊 BY SIGNAL <span class="sub2" style="font-weight:400">— each model's W–L · P&amp;L · CLV (take-on-sight, flat 1u — the signal record, not your placed bets)</span></h2>
<table><tr><th>signal</th><th>W–L</th><th>hit</th><th>P&amp;L</th><th>CLV</th><th>pend</th></tr>__SCOREBOARD__</table>

<div class="real"><h2>💰 REAL MONEY — your placed bets (COLD/SHRINK/STINGY)</h2>
__RSUMM__
<div class="sub2" style="margin-bottom:6px">⏳ pending = bot flagged it tonight — place &amp; record · settled = what you actually bet.<br><b>Signal CLV (the proof, take-on-sight):</b> __SIGCLVALL__</div>
<table><tr><th>slate</th><th>player</th><th>logged</th><th>bet @ odds</th><th>result</th><th>P&amp;L</th><th>CLV</th></tr>__RROWS__</table></div>

<div class="paper"><h2>🧪 PAPER TESTING — all other signals (NOT real money)</h2>
<div class="sub2" style="margin-bottom:6px">FLIP UNDER · FTUNDER · HOT OVER · BOOK OVERSHOOT · STAR-OUT CASCADE · usgshock — tracked for CLV, never staked.<br><b>logged</b> = MM-DD this bet was first captured (usually the day BEFORE the game — so a bet logged days ago only shows its result here once its game finishes, which is why they all surface together).</div>
__PSUMM__
<table><tr><th>slate</th><th>player</th><th>logged</th><th>bet @ odds</th><th>signal</th><th>result</th><th>P&amp;L</th><th>CLV</th></tr>__PROWS__</table></div>

<div class="foot">build_dashboard.py · REAL = COLD/SHRINK/STINGY (src=model); PAPER = everything else. P&amp;L is flat 1u stake vs the captured price. CLV &gt; 0 = we beat the close.</div>
</div></body></html>"""

page = (TEMPLATE.replace("__RSUMM__", summ_line(rs, "real")).replace("__RROWS__", real_rows)
        .replace("__PSUMM__", summ_line(ps, "paper")).replace("__PROWS__", paper_rows)
        .replace("__SLATE__", esc(slate)).replace("__THROUGH__", esc(through))
        .replace("__GEN__", gen).replace("__CLVHEAD__", clvhead)
        .replace("__SCOREBOARD__", scoreboard_html())
        .replace("__SIGCLVALL__", sig_clv_html(sig)))

with open(os.path.join(ROOT, "dashboard.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"dashboard.html written — REAL {rs['w']}-{rs['l']} ({rs['pnl']:+.2f}u) · PAPER {ps['w']}-{ps['l']} ({ps['pnl']:+.2f}u) · "
      f"{len(pending_real)} real + {len(pending_paper)} paper pending")
