# board.py - LOCAL BET BOARD (localhost:8899), styled to match the original dashboard.
# Sections: tonight's CLEARED (place these) / SKIPPED+paper fades / running plays / paper tracker.
# Dead plays (FTUNDER-as-bet, ML favourites, totals) are deliberately not shown - only a footnote.
# Auto-runs drift_gate.py on each load so the board is always current.
import csv, os, sys, math, statistics, subprocess, http.server, socketserver, datetime
D = os.path.dirname(os.path.abspath(__file__))
PORT = 8899
def f(x):
    try: return float(x)
    except Exception: return None
def RES(r): return (r.get("result") or "").upper()
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

CSS = """*{box-sizing:border-box}body{margin:0;background:#0d1020;color:#e8ecff;
font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:24px}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:16px;margin:26px 0 10px;color:#aeb6e0}
.sub{color:#7e87b8;font-size:13px;margin-bottom:16px}
.cards{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px}
.card{background:#151a31;border-radius:12px;padding:14px 18px;min-width:132px}
.card .k{color:#7e87b8;font-size:11px;text-transform:uppercase;letter-spacing:.4px}
.card .v{font-size:26px;font-weight:700;margin-top:2px}
table{border-collapse:collapse;width:100%;background:#151a31;border-radius:12px;overflow:hidden}
th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:#7e87b8;
padding:9px 12px;background:#0f1428}
td{padding:9px 12px;border-top:1px solid #1e2440;font-size:14px}
tr.bet td{background:#132a1e}tr.skip td{background:#2a1520;color:#8b93c2}
.g{color:#5fd07a;font-weight:600}.r{color:#f85149}.o{color:#ffb86b}.mut{color:#7e87b8;font-size:12px}
.tag{font-size:10px;padding:2px 8px;border-radius:10px;background:#1d2748;color:#7fe3f0}
.tagp{background:#3a2a12;color:#ffd9a8}.taglive{background:#14331f;color:#5fd07a}
.foot{color:#7e87b8;font-size:12px;margin-top:22px;line-height:1.7}"""

def stat(rows):
    v = [f(r["pnl"]) for r in rows if f(r.get("pnl")) is not None]
    n = len(v)
    if n < 3: return None
    m = statistics.mean(v); s = statistics.pstdev(v)
    w = sum(1 for r in rows if RES(r) == "WIN")
    return dict(n=n, w=w, l=n-w, wr=100*w/n, roi=100*m, pl=m*n, t=(m/(s/math.sqrt(n)) if s else 0))

def build():
    subprocess.run([sys.executable, os.path.join(D, "drift_gate.py")], capture_output=True, cwd=D, timeout=120)
    gp = os.path.join(D, "drift_gate_today.csv")
    gate = list(csv.DictReader(open(gp, encoding="utf-8"))) if os.path.exists(gp) else []
    LIVE = ("flip", "flip_paper", "cascade")
    cleared = [r for r in gate if r["verdict"].startswith("BET") and r["src"] in LIVE]
    other = [r for r in gate if r["verdict"].startswith("BET") and r["src"] not in LIVE]
    skipped = [r for r in gate if r["verdict"].startswith("SKIP")]
    slate = gate[0]["date"] if gate else "-"
    gbp = os.path.join(D, "graded_bets.csv")
    G = [r for r in csv.DictReader(open(gbp, encoding="utf-8")) if RES(r) in ("WIN", "LOSS")] if os.path.exists(gbp) else []
    def nd(rows): return [r for r in rows if (f(r.get("odds_clv")) or 0) >= -0.01]
    plays = [("FLIP · drift-cleared", stat(nd([r for r in G if r.get("src","").startswith("flip")])), 1),
             ("CASCADE · drift-cleared", stat(nd([r for r in G if r.get("src") == "cascade"])), 1),
             ("WHOLE BOOK · skip-drift ON", stat(nd(G)), 1),
             ("whole book · no filter (before)", stat(G), 0)]
    fgp = os.path.join(D, "fade_graded.csv")
    fg = [r for r in csv.DictReader(open(fgp, encoding="utf-8")) if r.get("result") in ("WIN", "loss")] if os.path.exists(fgp) else []
    fs = None
    if len(fg) >= 3:
        v = [f(r["ret"]) for r in fg if f(r.get("ret")) is not None]
        m = statistics.mean(v); s = statistics.pstdev(v)
        fs = dict(n=len(v), w=sum(1 for r in fg if r["result"] == "WIN"), roi=100*m, pl=m*len(v),
                  t=(m/(s/math.sqrt(len(v))) if s else 0))
    npend = 0
    if os.path.exists(fgp):
        npend = sum(1 for r in csv.DictReader(open(fgp, encoding="utf-8")) if not r.get("result"))
    h = [f"<!doctype html><meta charset=utf-8><title>WNBA bet board</title>",
         "<meta http-equiv=refresh content=180><style>", CSS, "</style><div class=wrap>",
         f"<h1>🏀 WNBA Bet Board</h1><div class=sub>slate <b>{esc(slate)}</b> · refreshed {datetime.datetime.now().strftime('%H:%M:%S')} · "
         f"skip-drift <span class='tag taglive'>LIVE</span> · auto-refresh 3min</div>"]
    h.append("<div class=cards>")
    h.append(f"<div class=card><div class=k>place tonight</div><div class='v g'>{len(cleared)}</div></div>")
    h.append(f"<div class=card><div class=k>skipped (drifted)</div><div class='v r'>{len(skipped)}</div></div>")
    if fs:
        h.append(f"<div class=card><div class=k>fade paper roi</div><div class='v {'g' if fs['roi']>0 else 'r'}'>{fs['roi']:+.0f}%</div></div>")
        h.append(f"<div class=card><div class=k>paper progress</div><div class='v o'>{fs['n']}<span class=mut>/100</span></div></div>")
    h.append("</div>")
    h.append("<h2>✅ CLEARED — place these</h2><table><tr><th>player<th>bet<th>odds<th>price move<th>signal</tr>")
    for r in sorted(cleared, key=lambda x: (x["src"], x["player"])):
        mv = f(r["move_pct"]) or 0
        cls = "g" if mv < 0 else "mut"
        h.append(f"<tr class=bet><td>{esc(r['player'])}<td>{esc(r['market'].upper())} {esc(r['side'])} {esc(r['line'])}"
                 f"<td class=g>{esc(r['now_odds'])}<td class={cls}>{mv:+.1f}%<td><span class=tag>{esc(r['src'])}</span></tr>")
    if not cleared: h.append("<tr><td colspan=5 class=mut>no cleared bets for this slate yet</td></tr>")
    h.append("</table>")
    h.append("<h2>🚫 SKIPPED — market walked away (fade logged to paper)</h2><table><tr><th>player<th>their bet<th>drift<th>signal<th>paper fade</tr>")
    for r in skipped:
        fd = f"{r['fade_side']} @ {r['fade_price']}" if r["fade_side"] else "—"
        h.append(f"<tr class=skip><td>{esc(r['player'])}<td>{esc(r['market'].upper())} {esc(r['side'])} {esc(r['line'])}"
                 f"<td class=r>{esc(r['move_pct'])}%<td>{esc(r['src'])}<td><span class='tag tagp'>{esc(fd)}</span></tr>")
    if not skipped: h.append("<tr><td colspan=5 class=mut>nothing drifted this slate</td></tr>")
    h.append("</table>")
    if other: h.append(f"<div class=sub style='margin-top:8px'>+{len(other)} other cleared signals not in the live menu (tracking only)</div>")
    h.append("<h2>📊 RUNNING PLAYS</h2><table><tr><th>play<th>W–L<th>win%<th>ROI<th>P&amp;L<th>t<th>status</tr>")
    for name, s, live in plays:
        if not s: continue
        c = "g" if s["roi"] > 0 else "r"
        tag = "<span class='tag taglive'>LIVE</span>" if live else "<span class=mut>superseded</span>"
        h.append(f"<tr><td>{name}<td>{s['w']}-{s['l']}<td>{s['wr']:.0f}%<td class={c}>{s['roi']:+.1f}%"
                 f"<td class={c}>{s['pl']:+.1f}u<td>{s['t']:+.2f}<td>{tag}</tr>")
    if fs:
        c = "g" if fs["roi"] > 0 else "r"
        h.append(f"<tr><td>FADE-DRIFT · forward paper<td>{fs['w']}-{fs['n']-fs['w']}<td>{100*fs['w']/fs['n']:.0f}%"
                 f"<td class={c}>{fs['roi']:+.1f}%<td class={c}>{fs['pl']:+.1f}u<td>{fs['t']:+.2f}"
                 f"<td><span class='tag tagp'>PAPER {fs['n']}/100</span></tr>")
    elif npend:
        h.append(f"<tr><td>FADE-DRIFT · forward paper<td colspan=5 class=mut>{npend} logged, awaiting results</td></tr>")
    h.append("</table>")
    h.append("<div class=foot>❌ never bet: FTUNDER as a bet (−13.5% ROI, t−2.18) · ML favourites (−5.2%, t−2.93) · totals either side.<br>"
             "Go-live gate for the fade: t ≥ 2 <b>and</b> n ≥ 100 forward <b>and</b> ROI &gt; +10%.</div></div>")
    return "".join(h)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        try: body = build().encode("utf-8")
        except Exception:
            import traceback; body = f"<pre style='color:#f85149;background:#0d1020'>{traceback.format_exc()}</pre>".encode()
        s.send_response(200); s.send_header("Content-Type", "text/html; charset=utf-8")
        s.send_header("Content-Length", str(len(body))); s.end_headers(); s.wfile.write(body)
    def log_message(s, *a): pass

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as srv:
        print(f"bet board -> http://localhost:{PORT}")
        srv.serve_forever()
