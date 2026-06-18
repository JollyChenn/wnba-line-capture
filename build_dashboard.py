# -*- coding: utf-8 -*-
"""
build_dashboard.py — generate a self-contained dashboard.html from the bot's CSVs.
No external libs, no runtime data loading (numbers baked in) -> opens from file://
or serves as a static page. Re-run anytime; wire into a workflow to auto-publish.

Honest by construction: PROVEN (model+flip) and PAPER are walled off, and CLV —
the only real proof — is the hero metric, not P&L.
"""
import csv, os, html, datetime
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
def load(p):
    fp = os.path.join(ROOT, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []

graded = load("graded_bets.csv")
picks  = load("picks_log.csv")
casc   = load("cascade_log.csv")
mybets = load("my_bets.csv")
PROVEN = {"model", "flip"}
esc = lambda s: html.escape(str(s))

# ---- record by src ---------------------------------------------------------
rec = defaultdict(lambda: {"w": 0, "l": 0, "push": 0, "pnl": 0.0, "clv": []})
for r in graded:
    d = rec[(r.get("src") or "?")]
    res = r.get("result", "")
    if res == "WIN": d["w"] += 1
    elif res in ("loss", "LOSS"): d["l"] += 1
    elif res == "push": d["push"] += 1
    try: d["pnl"] += float(r.get("pnl") or 0)
    except ValueError: pass
    oc = r.get("odds_clv", "")
    if oc not in ("", "None", None):
        try: d["clv"].append(float(oc))
        except ValueError: pass

def agg(srcs):
    w = l = 0; pnl = 0.0; clv = []
    for s in srcs:
        if s in rec:
            w += rec[s]["w"]; l += rec[s]["l"]; pnl += rec[s]["pnl"]; clv += rec[s]["clv"]
    n = w + l
    return dict(w=w, l=l, n=n, hit=(w / n if n else None), pnl=pnl,
                clv=(sum(clv) / len(clv) if clv else None), nclv=len(clv),
                beat=(sum(1 for x in clv if x > 0) / len(clv) if clv else None))

proven = agg(PROVEN)
paper  = agg([s for s in rec if s not in PROVEN])
overall = agg(list(rec))
BE = 0.556  # 1xbet flat ~1.80 breakeven

# ---- today's picks (latest pick_date) --------------------------------------
dates = sorted({p["pick_date"] for p in picks if p.get("pick_date")})
latest = dates[-1] if dates else None
today = [p for p in picks if p.get("pick_date") == latest]
def bucket(p):
    sig, mk = p.get("signals", ""), p.get("market", "")
    if sig in ("ftdrought", "steady"): return ("paper", "newunder")
    if sig == "usgshock": return ("paper", "usgshock")
    if mk.endswith("_over"): return ("real", "hot over")
    return ("real", "model under")
real_picks  = [p for p in today if bucket(p)[0] == "real"]
paper_picks = [p for p in today if bucket(p)[0] == "paper"]

# OUT line from PICKS.md (the bot already wrote it)
out_line = ""
mdp = os.path.join(ROOT, "PICKS.md")
if os.path.exists(mdp):
    for ln in open(mdp, encoding="utf-8"):
        if "OUT/doubtful" in ln:
            out_line = ln.strip().strip("_"); break

# ---- html fragments --------------------------------------------------------
def pct(x): return "—" if x is None else f"{x*100:.0f}%"
def clvfmt(x): return "—" if x is None else f"{x*100:+.1f}%"
def cls(x, good_hi=True, thr=0.0):
    if x is None: return "muted"
    return "pos" if (x > thr) == good_hi else "neg"

def card(label, value, sub, klass=""):
    return (f'<div class="card"><div class="lbl">{esc(label)}</div>'
            f'<div class="val {klass}">{value}</div><div class="sub">{esc(sub)}</div></div>')

cards = "".join([
    card("Proven CLV  ⟵ the proof", clvfmt(proven["clv"]),
         f'beat the close {proven["beat"]*100:.0f}% · n={proven["nclv"]}' if proven["beat"] is not None else "no CLV yet",
         cls(proven["clv"])),
    card("Proven record", f'{proven["w"]}–{proven["l"]}',
         f'{pct(proven["hit"])} hit · {proven["pnl"]:+.1f}u (synthetic)', cls((proven["hit"] or 0) - BE)),
    card("Paper / experimental", f'{paper["w"]}–{paper["l"]}',
         f'{pct(paper["hit"])} hit · CLV {clvfmt(paper["clv"])} · walled off', "muted"),
    card("All settled", f'{overall["w"]}–{overall["l"]}',
         f'{overall["n"]} bets graded', "muted"),
])

# record-by-src table
rows = ""
order = sorted(rec, key=lambda s: (s not in PROVEN, -(rec[s]["w"] + rec[s]["l"])))
for s in order:
    d = rec[s]; n = d["w"] + d["l"]; hit = d["w"] / n if n else None
    clv = sum(d["clv"]) / len(d["clv"]) if d["clv"] else None
    tag = "PROVEN" if s in PROVEN else "paper"
    rows += (f'<tr><td>{esc(s)}</td><td><span class="pill {"pos" if s in PROVEN else "mut"}">{tag}</span></td>'
             f'<td>{d["w"]}–{d["l"]}</td><td class="{cls((hit or 0)-BE)}">{pct(hit)}</td>'
             f'<td class="{cls(clv)}">{clvfmt(clv)}</td><td class="{cls(d["pnl"])}">{d["pnl"]:+.1f}u</td></tr>')

# CLV bar chart (SVG) — mean CLV% per src
bars = [(s, (sum(rec[s]["clv"]) / len(rec[s]["clv"]) * 100) if rec[s]["clv"] else None) for s in order]
bars = [(s, v) for s, v in bars if v is not None]
svg = ""
if bars:
    W, H, pad, bw = 460, 40 + 34 * len(bars), 120, 18
    mx = max(6, max(abs(v) for _, v in bars))
    zero = pad + (W - pad - 20) * 0  # left axis at pad; we map [-mx,mx] across pad..W-20
    span = (W - pad - 20)
    def x_of(v): return pad + span * (v + mx) / (2 * mx)
    z = x_of(0)
    parts = [f'<line x1="{z:.0f}" y1="28" x2="{z:.0f}" y2="{H-8}" stroke="#39406b"/>']
    for i, (s, v) in enumerate(bars):
        y = 34 + i * 34; xv = x_of(v)
        x0, x1 = (z, xv) if v >= 0 else (xv, z)
        col = "#3fb950" if v > 0 else "#f85149"
        parts.append(f'<rect x="{x0:.0f}" y="{y:.0f}" width="{abs(x1-x0):.0f}" height="18" rx="3" fill="{col}"/>')
        parts.append(f'<text x="8" y="{y+13:.0f}" fill="#aeb6e0" font-size="12">{esc(s)}</text>')
        parts.append(f'<text x="{(xv + (6 if v>=0 else -6)):.0f}" y="{y+13:.0f}" fill="#e8ecff" font-size="11" text-anchor="{"start" if v>=0 else "end"}">{v:+.1f}%</text>')
    svg = f'<svg viewBox="0 0 {W} {H}" width="100%">{"".join(parts)}</svg>'

def picklist(items):
    if not items:
        return '<div class="empty">— none —</div>'
    out = ""
    for p in items:
        _, label = bucket(p)
        side = "Over" if p.get("market","").endswith("_over") else "Under"
        mk = p.get("market","").split("_")[0].upper()
        out += (f'<div class="pick"><b>{esc(p.get("player",""))}</b> '
                f'<span class="mut">{esc(p.get("team",""))}</span> · {mk} {side} '
                f'<b>{esc(p.get("anchor",""))}</b> @ {esc(p.get("fair_odds",""))} '
                f'<span class="pill mut">{esc(label)}</span></div>')
    return out

# recent settled (last 12 by date)
recent = sorted(graded, key=lambda r: r.get("date",""))[-12:][::-1]
rrows = ""
for r in recent:
    res = r.get("result","")
    rcls = "pos" if res=="WIN" else ("neg" if res in ("loss","LOSS") else "muted")
    oc = r.get("odds_clv","")
    try: ocf = clvfmt(float(oc)) if oc not in ("","None",None) else "—"
    except ValueError: ocf = "—"
    rrows += (f'<tr><td>{esc(r.get("date",""))}</td><td>{esc(r.get("player",""))}</td>'
              f'<td>{esc(r.get("market","").upper())} {esc(r.get("side",""))} {esc(r.get("line",""))}</td>'
              f'<td>{esc(r.get("actual",""))}</td><td class="{rcls}">{esc(res)}</td>'
              f'<td><span class="pill {"pos" if (r.get("src") in PROVEN) else "mut"}">{esc(r.get("src",""))}</span></td>'
              f'<td>{ocf}</td></tr>')

gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
data_through = max((r.get("date","") for r in graded), default="—")

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WNBA prop bot — dashboard</title><style>
*{box-sizing:border-box} body{margin:0;background:#0d1020;color:#e8ecff;
font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1040px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 2px} h2{font-size:15px;color:#aeb6e0;margin:26px 0 10px;
text-transform:uppercase;letter-spacing:.06em}
.sub2{color:#7e87b8;font-size:13px}
.banner{background:#1a1430;border:1px solid #4a2; border-color:#5b4b8a;border-radius:12px;
padding:14px 16px;margin:16px 0;color:#ffd9a8}
.banner b{color:#ffb86b}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.card{background:#151a31;border:1px solid #262d4f;border-radius:12px;padding:14px 16px}
.card .lbl{color:#8b93c2;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.card .val{font-size:28px;font-weight:700;margin:4px 0}
.card .sub{color:#7e87b8;font-size:12px}
table{width:100%;border-collapse:collapse;background:#151a31;border:1px solid #262d4f;border-radius:12px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid #20264400} th{color:#8b93c2;font-size:12px;
text-transform:uppercase;letter-spacing:.04em;background:#11152a} tr:nth-child(even) td{background:#12172c}
td{font-size:14px}
.pos{color:#3fb950} .neg{color:#f85149} .muted,.mut{color:#7e87b8}
.pill{font-size:11px;padding:2px 7px;border-radius:20px;background:#222a4d;color:#aeb6e0}
.pill.pos{background:#143d22;color:#5fd07a} .pill.mut{background:#222a4d}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.box{background:#151a31;border:1px solid #262d4f;border-radius:12px;padding:12px 14px}
.box h3{margin:0 0 8px;font-size:13px;color:#aeb6e0}
.pick{padding:6px 0;border-bottom:1px solid #20264433;font-size:14px}
.empty{color:#7e87b8;padding:8px 0} .foot{color:#5a628f;font-size:12px;margin-top:24px}
@media(max-width:640px){.cols{grid-template-columns:1fr}}
</style></head><body><div class="wrap">
<h1>🏀 WNBA prop bot</h1><div class="sub2">slate __LATEST__ · data through __THROUGH__ · generated __GEN__</div>
<div class="banner">⚠️ <b>UNPROVEN — paper / tiny only.</b> Every hit% is vs a synthetic median line (predicts the SIDE, not that it beats the book). <b>CLV is the only proof</b> — and it's __CLVHEAD__ so far. Never auto-bet.</div>
<div class="grid">__CARDS__</div>
<h2>Record by signal</h2>
<table><tr><th>signal</th><th>tier</th><th>W–L</th><th>hit%</th><th>odds-CLV</th><th>P&amp;L*</th></tr>__ROWS__</table>
<div class="sub2" style="margin-top:6px">*P&amp;L is vs a synthetic line, not realized cash. Breakeven at 1xbet ~1.80 = 55.6%.</div>
<h2>Mean CLV by signal (the number that matters)</h2><div class="box">__SVG__</div>
<h2>Today's slate — __LATEST__</h2>
<div class="sub2" style="margin-bottom:10px">🩹 __OUT__</div>
<div class="cols">
<div class="box"><h3>✅ Real-money (model / flip)</h3>__REAL__</div>
<div class="box"><h3>🧪 Paper / experimental</h3>__PAPER__</div>
</div>
<h2>Recent settled</h2>
<table><tr><th>date</th><th>player</th><th>bet</th><th>act</th><th>result</th><th>signal</th><th>CLV</th></tr>__RECENT__</table>
<div class="foot">Generated by build_dashboard.py from graded_bets / picks_log / PICKS.md. Proven = model+flip; everything else is walled-off paper. CLV &gt; 0 = we beat the close.</div>
</div></body></html>"""

clvhead = (clvfmt(proven["clv"]) + (" (negative)" if (proven["clv"] or 0) < 0 else "")) if proven["clv"] is not None else "not measured yet"
page = (TEMPLATE.replace("__CARDS__", cards).replace("__ROWS__", rows).replace("__SVG__", svg or "<div class='empty'>no CLV data yet</div>")
        .replace("__REAL__", picklist(real_picks)).replace("__PAPER__", picklist(paper_picks))
        .replace("__RECENT__", rrows or "<tr><td colspan=7 class='empty'>none</td></tr>")
        .replace("__LATEST__", esc(latest or "—")).replace("__THROUGH__", esc(data_through))
        .replace("__GEN__", gen).replace("__OUT__", esc(out_line or "no OUT/doubtful flagged"))
        .replace("__CLVHEAD__", clvhead))

open(os.path.join(ROOT, "dashboard.html"), "w", encoding="utf-8").write(page)
print(f"dashboard.html written — proven {proven['w']}-{proven['l']} CLV {clvfmt(proven['clv'])}, "
      f"{len(real_picks)} real + {len(paper_picks)} paper picks for {latest}")
