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

# ---- pending = the LATEST slate's captures not yet settled (not ancient un-graded rows) ----
slate_date = max((r.get("date","") for r in bets_log if r.get("player")), default="")
settled_keys = {(r.get("date","").replace("-",""), r.get("player","").lower(), r.get("market","")) for r in graded}
seen = set(); pending = []
for r in reversed(bets_log):                            # newest capture per player+market, latest slate only
    if r.get("date","") != slate_date:
        continue
    k = (r.get("date","").replace("-",""), r.get("player","").lower(), r.get("market",""))
    if not r.get("player") or k in settled_keys or k in seen:
        continue
    seen.add(k); pending.append(r)
pending.sort(key=lambda r: (r.get("player","")))
mb_players = {r.get("player","").lower() for r in mybets}
pending_real  = [r for r in pending if is_real(r.get("src","")) and r.get("player","").lower() not in mb_players]  # tonight's flags to place
pending_paper = [r for r in pending if not is_real(r.get("src",""))]

# ---- per-section summary (flat 1u stake) -----------------------------------
def summarize(settled):
    w = sum(1 for r in settled if r.get("result") == "WIN")
    l = sum(1 for r in settled if r.get("result") in ("loss", "LOSS"))
    pnl = sum(float(r.get("pnl") or 0) for r in settled)
    clv = [float(r["odds_clv"]) for r in settled if r.get("odds_clv") not in ("", "None", None)]
    n = w + l
    return dict(w=w, l=l, n=n, hit=(w/n if n else None), pnl=pnl,
                clv=(sum(clv)/len(clv) if clv else None), nclv=len(clv))

rs, ps = summarize(settled_real), summarize(settled_paper)
sig = summarize(signal_model)                          # signal CLV proof (take-on-sight, separate from your actual P&L)
BE = 0.556

# ---- formatting helpers ----------------------------------------------------
def pct(x):  return "—" if x is None else f"{x*100:.0f}%"
def clvfmt(x): return "—" if x is None else f"{x*100:+.1f}%"
def betname(r): return f'{r.get("market","").upper()} {r.get("side","")} {r.get("line","")}'
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
        out.append(f'<tr class="pend"><td>{esc(r.get("date",""))}</td><td><b>{esc(r.get("player",""))}</b></td>'
                   f'<td>{esc(betname(r))} @ {esc(r.get("odds",""))}</td>{sig}'
                   f'<td><span class="pill">⏳ pending</span></td><td class="muted">—</td><td class="muted">—</td></tr>')
    for r in sorted(settled, key=lambda x: x.get("date",""), reverse=True):
        txt, cl = resfmt(r.get("result",""))
        try: pnl = float(r.get("pnl") or 0)
        except ValueError: pnl = 0.0
        oc = r.get("odds_clv","")
        try: ocf = clvfmt(float(oc)) if oc not in ("","None",None) else "—"
        except ValueError: ocf = "—"
        sig = f'<td>{esc(signame(srcof(r)))}</td>' if with_sig else ''
        out.append(f'<tr><td>{esc(r.get("date",""))}</td><td><b>{esc(r.get("player",""))}</b></td>'
                   f'<td>{esc(betname(r))} @ {esc(r.get("odds",""))}</td>{sig}'
                   f'<td class="{cl}">{txt}</td><td class="{"pos" if pnl>0 else ("neg" if pnl<0 else "muted")}">{pnl:+.2f}u</td>'
                   f'<td class="{("pos" if (oc not in ("","None",None) and float(oc or 0)>0) else "muted")}">{ocf}</td></tr>')
    if not out:
        cols = 7 if with_sig else 6
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

<div class="real"><h2>💰 REAL MONEY — your placed bets (COLD/SHRINK/STINGY)</h2>
__RSUMM__
<div class="sub2" style="margin-bottom:6px">⏳ pending = bot flagged it tonight — place &amp; record · settled = what you actually bet. <b>Signal CLV (the proof, take-on-sight): __SIGCLV__</b> · n=__SIGN__</div>
<table><tr><th>slate</th><th>player</th><th>bet @ odds</th><th>result</th><th>P&amp;L</th><th>CLV</th></tr>__RROWS__</table></div>

<div class="paper"><h2>🧪 PAPER TESTING — all other signals (NOT real money)</h2>
<div class="sub2" style="margin-bottom:6px">FLIP UNDER · FTUNDER · HOT OVER · BOOK OVERSHOOT · STAR-OUT CASCADE · usgshock — tracked for CLV, never staked.</div>
__PSUMM__
<table><tr><th>slate</th><th>player</th><th>bet @ odds</th><th>signal</th><th>result</th><th>P&amp;L</th><th>CLV</th></tr>__PROWS__</table></div>

<div class="foot">build_dashboard.py · REAL = COLD/SHRINK/STINGY (src=model); PAPER = everything else. P&amp;L is flat 1u stake vs the captured price. CLV &gt; 0 = we beat the close.</div>
</div></body></html>"""

page = (TEMPLATE.replace("__RSUMM__", summ_line(rs, "real")).replace("__RROWS__", real_rows)
        .replace("__PSUMM__", summ_line(ps, "paper")).replace("__PROWS__", paper_rows)
        .replace("__SLATE__", esc(slate)).replace("__THROUGH__", esc(through))
        .replace("__GEN__", gen).replace("__CLVHEAD__", clvhead)
        .replace("__SIGCLV__", clvfmt(sig["clv"])).replace("__SIGN__", str(sig["n"])))

with open(os.path.join(ROOT, "dashboard.html"), "w", encoding="utf-8") as f:
    f.write(page)
print(f"dashboard.html written — REAL {rs['w']}-{rs['l']} ({rs['pnl']:+.2f}u) · PAPER {ps['w']}-{ps['l']} ({ps['pnl']:+.2f}u) · "
      f"{len(pending_real)} real + {len(pending_paper)} paper pending")
