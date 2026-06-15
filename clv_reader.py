# clv_reader.py — read graded_bets.csv and show the track record + a plain-English CLV verdict.
# Read-only (does NOT re-grade). Run anytime: `python clv_reader.py`. Pings Discord if DISCORD_WEBHOOK set.
import csv, os, json, urllib.request
from collections import defaultdict

if not os.path.exists("graded_bets.csv"):
    print("no graded bets yet — track record starts after the first slate settles"); raise SystemExit
rows = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8")))
dec = [r for r in rows if r["result"] in ("WIN", "loss")]
if not dec:
    print("no settled bets yet (only pushes/pending)"); raise SystemExit

n = len(dec); w = sum(1 for r in dec if r["result"] == "WIN"); net = sum(float(r["pnl"]) for r in dec)
oc = [float(r["odds_clv"]) for r in rows if r.get("odds_clv") not in ("", None)]
avg_clv = sum(oc) / len(oc) if oc else 0.0
beat = sum(1 for x in oc if x > 0)
beat_pct = beat / len(oc) if oc else 0

L = []
L.append(f"📊 **WNBA BOT — TRACK RECORD** ({n} settled)")
L.append(f"  Record  : {w}-{n - w}  ({w / n * 100:.0f}% hit)")
L.append(f"  Net P&L : {net:+.2f}u  (ROI {net / n * 100:+.1f}%/bet)")
if oc:
    L.append(f"  ODDS-CLV: {avg_clv * 100:+.1f}% avg | beat close {beat}/{len(oc)} ({beat_pct * 100:.0f}%)  ← the edge signal")

# VERDICT — CLV is the proof; hit-rate at small n is noise
if n < 20:
    lean = "leaning +" if avg_clv > 0.01 else "leaning −" if avg_clv < -0.01 else "flat"
    verdict = f"⏳ TOO EARLY (n={n}, need ~20-40 ≈ 2wks). Early CLV {lean} — not yet meaningful."
elif avg_clv > 0.02 and beat_pct > 0.55:
    verdict = "✅ POSITIVE CLV — we're beating the close. Edge looks REAL — consider scaling."
elif avg_clv < -0.01 or beat_pct < 0.45:
    verdict = "❌ NEGATIVE CLV — the market beats us. No real edge — kill or rebuild."
else:
    verdict = "⚠️ NEUTRAL CLV — winning on outcomes, not beating the line. Unproven; keep collecting."
L.append(f"  VERDICT : {verdict}")

# by tier + by market
for label, key in [("tier", "tier"), ("market", None)]:
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in dec:
        k = (r["tier"] or "?") if key else f"{r['market']} {r['side']}"
        agg[k][0] += 1; agg[k][1] += r["result"] == "WIN"; agg[k][2] += float(r["pnl"])
    L.append(f"  by {label}: " + " · ".join(f"{k} {ww}/{t} ({p:+.1f}u)" for k, (t, ww, p) in sorted(agg.items())))

print("\n".join(L))
print("\n  PER-BET (CLV>0 = our price beat the close):")
print(f"  {'date':9}{'player':18}{'bet':15}{'res':5}{'CLV':>6}")
for r in sorted(rows, key=lambda r: (r["date"], r["player"])):
    oclv = f"{float(r['odds_clv']) * 100:+.0f}%" if r.get("odds_clv") not in ("", None) else "  --"
    print(f"  {r['date']:9}{r['player'][:17]:18}{(r['market'].upper() + ' ' + r['side'])[:14]:15}{r['result'][:4]:5}{oclv:>6}")

hook = os.environ.get("DISCORD_WEBHOOK", "")
if hook:
    try:
        urllib.request.urlopen(urllib.request.Request(hook, data=json.dumps({"content": "\n".join(L)[:1900]}).encode(),
                               headers={"Content-Type": "application/json"}), timeout=15)
        print("\n  (pinged Discord)")
    except Exception as e:
        print("\n  discord:", e)
