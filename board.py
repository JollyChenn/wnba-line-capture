# board.py - LOCAL BET BOARD (localhost:8899). One page, only what you act on:
#   1. tonight's CLEARED bets (flip + cascade, drift-passed)  <- what you actually place
#   2. tonight's SKIPPED bets + their paper fades
#   3. live scoreboard of the 3 running plays + the fade paper record
# Everything dead (FTUNDER as a bet, ML favs, totals) is intentionally NOT shown.
# Run:  python board.py    then open http://localhost:8899
import csv, os, sys, math, statistics, subprocess, http.server, socketserver, datetime
from collections import defaultdict
D = os.path.dirname(os.path.abspath(__file__))
PORT = 8899
def f(x):
    try: return float(x)
    except Exception: return None
def RES(r): return (r.get("result") or "").upper()

def stat(rows, key="pnl"):
    v = [f(r[key]) for r in rows if f(r.get(key)) is not None]
    n = len(v)
    if n < 3: return None
    m = statistics.mean(v); s = statistics.pstdev(v)
    w = sum(1 for r in rows if RES(r) == "WIN")
    return dict(n=n, w=w, l=n-w, wr=100*w/n if n else 0, roi=100*m, pl=m*n,
                t=(m/(s/math.sqrt(n)) if s else 0))

def build():
    subprocess.run([sys.executable, os.path.join(D, "drift_gate.py")], capture_output=True, cwd=D)
    gate = list(csv.DictReader(open(os.path.join(D, "drift_gate_today.csv"), encoding="utf-8"))) \
        if os.path.exists(os.path.join(D, "drift_gate_today.csv")) else []
    LIVE_SRC = ("flip", "flip_paper", "cascade")
    cleared = [r for r in gate if r["verdict"].startswith("BET") and r["src"] in LIVE_SRC]
    other   = [r for r in gate if r["verdict"].startswith("BET") and r["src"] not in LIVE_SRC]
    skipped = [r for r in gate if r["verdict"].startswith("SKIP")]
    slate = gate[0]["date"] if gate else "-"
    G = [r for r in csv.DictReader(open(os.path.join(D, "graded_bets.csv"), encoding="utf-8"))
         if RES(r) in ("WIN", "LOSS")] if os.path.exists(os.path.join(D, "graded_bets.csv")) else []
    nd = len({r["date"] for r in G}) or 1
    def nodrift(rows): return [r for r in rows if (f(r.get("odds_clv")) or 0) >= -0.01]
    plays = [
        ("FLIP (drift-cleared)", stat(nodrift([r for r in G if r.get("src","").startswith("flip")])), "LIVE"),
        ("CASCADE (drift-cleared)", stat(nodrift([r for r in G if r.get("src") == "cascade"])), "LIVE"),
        ("WHOLE BOOK w/ skip-drift", stat(nodrift(G)), "LIVE"),
        ("whole book, no filter (before)", stat(G), "off"),
    ]
    fg = list(csv.DictReader(open(os.path.join(D, "fade_graded.csv"), encoding="utf-8"))) \
        if os.path.exists(os.path.join(D, "fade_graded.csv")) else []
    fset = [r for r in fg if r.get("result") in ("WIN", "loss")]
    fs = None
    if len(fset) >= 3:
        v = [f(r["ret"]) for r in fset if f(r.get("ret")) is not None]
        m = statistics.mean(v); s = statistics.pstdev(v)
        fs = dict(n=len(v), w=sum(1 for r in fset if r["result"] == "WIN"),
                  roi=100*m, pl=m*len(v), t=(m/(s/math.sqrt(len(v))) if s else 0))
    css = """<style>body{background:#0d1117;color:#c9d1d9;font:14px/1.5 -apple-system,Segoe UI,sans-serif;margin:0;padding:24px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:26px 0 8px;color:#58a6ff}
.sub{color:#8b949e;font-size:12px;margin-bottom:18px}
table{border-collapse:collapse;width:100%;margin-bottom:8px}
th{text-align:left;font-size:11px;text-transform:uppercase;color:#8b949e;padding:6px 10px;border-bottom:1px solid #30363d}
td{padding:7px 10px;border-bottom:1px solid #21262d}
.bet{background:#0f2417}.skip{background:#2a1215;color:#8b949e}
.g{color:#3fb950;font-weight:600}.r{color:#f85149}.y{color:#d29922}
.tag{font-size:10px;padding:2px 7px;border-radius:9px;background:#1f6feb33;color:#58a6ff}
.tagp{background:#d2992233;color:#d29922}.mut{color:#8b949e;font-size:12px}
.big{font-size:26px;font-weight:700}.card{display:inline-block;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px 20px;margin:0 10px 10px 0}
</style>"""
    h = [f"<!doctype html><meta charset=utf-8><title>WNBA bet board</title>{css}",
         f"<h1>WNBA Bet Board</h1><div class=sub>slate {slate} &middot; refreshed {datetime.datetime.now().strftime('%H:%M:%S')} &middot; skip-drift LIVE</div>"]
    h.append(f"<div class=card><div class=mut>PLACE TONIGHT</div><div class='big g'>{len(cleared)}</div></div>")
    h.append(f"<div class=card><div class=mut>SKIPPED (drifted)</div><div class='big r'>{len(skipped)}</div></div>")
    if fs: h.append(f"<div class=card><div class=mut>fade paper (n={fs['n']})</div><div class='big {'g' if fs['roi']>0 else 'r'}'>{fs['roi']:+.0f}%</div></div>")
    h.append("<h2>&#9989; CLEARED &mdash; place these</h2><table><tr><th>player<th>bet<th>odds<th>move<th>signal</tr>")
    for r in sorted(cleared, key=lambda x: x["src"]):
        h.append(f"<tr class=bet><td>{r['player']}<td>{r['market'].upper()} {r['side']} {r['line']}"
                 f"<td class=g>{r['now_odds']}<td class=mut>{r['move_pct']}%<td><span class=tag>{r['src']}</span></tr>")
    if not cleared: h.append("<tr><td colspan=5 class=mut>no cleared bets for this slate</td></tr>")
    h.append("</table>")
    h.append("<h2>&#128683; SKIPPED (price drifted) &mdash; do not bet; fade logged to paper</h2><table><tr><th>player<th>their bet<th>drift<th>signal<th>paper fade</tr>")
    for r in skipped:
        fd = f"{r['fade_side']} @ {r['fade_price']}" if r["fade_side"] else "-"
        h.append(f"<tr class=skip><td>{r['player']}<td>{r['market'].upper()} {r['side']} {r['line']}"
                 f"<td class=r>{r['move_pct']}%<td>{r['src']}<td><span class=tagp>{fd}</span></tr>")
    if not skipped: h.append("<tr><td colspan=5 class=mut>nothing drifted this slate</td></tr>")
    h.append("</table>")
    if other:
        h.append(f"<h2 class=mut>other cleared signals (not in the live menu &mdash; tracking only): {len(other)}</h2>")
    h.append("<h2>&#128200; running plays</h2><table><tr><th>play<th>W-L<th>win%<th>ROI<th>P&amp;L<th>t<th></tr>")
    for name, s, status in plays:
        if not s: continue
        c = "g" if s["roi"] > 0 else "r"
        tag = "<span class=tag>LIVE</span>" if status == "LIVE" else "<span class=mut>off</span>"
        h.append(f"<tr><td>{name}<td>{s['w']}-{s['l']}<td>{s['wr']:.0f}%<td class={c}>{s['roi']:+.1f}%"
                 f"<td class={c}>{s['pl']:+.1f}u<td>{s['t']:+.2f}<td>{tag}</tr>")
    if fs:
        c = "g" if fs["roi"] > 0 else "r"
        h.append(f"<tr><td>FADE-DRIFT (forward paper)<td>{fs['w']}-{fs['n']-fs['w']}<td>{100*fs['w']/fs['n']:.0f}%"
                 f"<td class={c}>{fs['roi']:+.1f}%<td class={c}>{fs['pl']:+.1f}u<td>{fs['t']:+.2f}"
                 f"<td><span class=tagp>PAPER {fs['n']}/100</span></tr>")
    h.append("</table>")
    h.append("<div class=sub style='margin-top:20px'>never bet: FTUNDER as a bet (-13.5% ROI t-2.18) &middot; "
             "ML favourites (-5.2% t-2.93) &middot; totals either side. Proof gate: t&ge;2 &amp; n&ge;100 forward &amp; ROI&gt;+10%.</div>")
    return "".join(h)

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(s):
        try: body = build().encode("utf-8")
        except Exception as e:
            import traceback; body = f"<pre>{traceback.format_exc()}</pre>".encode()
        s.send_response(200); s.send_header("Content-Type", "text/html; charset=utf-8")
        s.send_header("Content-Length", str(len(body))); s.end_headers(); s.wfile.write(body)
    def log_message(s, *a): pass

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as srv:
        print(f"bet board -> http://localhost:{PORT}   (ctrl-c to stop)")
        srv.serve_forever()
