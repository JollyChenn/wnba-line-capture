# clv_reader.py — read graded_bets.csv and show the track record + a plain-English CLV verdict.
# Read-only (does NOT re-grade). Run anytime: `python clv_reader.py`. Pings Discord if DISCORD_WEBHOOK set.
import csv, os, json, urllib.request
from collections import defaultdict

if not os.path.exists("graded_bets.csv"):
    print("no graded bets yet — track record starts after the first slate settles"); raise SystemExit
rows = list(csv.DictReader(open("graded_bets.csv", encoding="utf-8")))


def _src(r):                                          # legacy graded rows (no src col): under=model, over=overshoot
    return r.get("src", "") or ("model" if r["side"] == "Under" else "overshoot")


SRC_LABEL = {                                         # proper display names (renamed 2026-06-19; internal keys stay stable)
    "model": "COLD/SHRINK/STINGY", "flip": "FLIP UNDER", "flip_paper": "FLIP UNDER(paper)",
    "newunder": "FTUNDER", "hotover": "HOT OVER", "usgshock": "usgshock", "cascade": "STAR-OUT CASCADE",
    "starout": "starout", "overshoot": "BOOK OVERSHOOT", "fragile": "fragile",
}
def lab(s): return SRC_LABEL.get(s, s)


PROVEN = {"model"}                                    # headline = REAL-MONEY signal ONLY (COLD/SHRINK/STINGY); flip/etc = paper
proven = [r for r in rows if _src(r) in PROVEN]       # speculative overs (hotover/overshoot) NEVER touch the headline
exper = [r for r in rows if _src(r) not in PROVEN]
dec = [r for r in proven if r["result"] in ("WIN", "loss")]

# experimental (unproven) overs — surfaced separately so a hot/overshoot streak never poses as the bot's record
exp_dec = [r for r in exper if r["result"] in ("WIN", "loss")]


def _bucket(rs):
    by = defaultdict(lambda: [0, 0, 0.0])
    for r in rs:
        k = lab(_src(r)); by[k][0] += 1; by[k][1] += r["result"] == "WIN"; by[k][2] += float(r["pnl"])
    return by


if not dec:
    L0 = ["📊 **WNBA BOT — TRACK RECORD**",
          "  PROVEN signals (cold+shrink under / flip): _none settled yet — headline starts when one does._"]
    if exp_dec:
        b = _bucket(exp_dec)
        L0.append("  Experimental overs (UNPROVEN): " + " · ".join(
            f"{k} {ww}/{t} ({p:+.1f}u)" for k, (t, ww, p) in sorted(b.items())))
    print("\n".join(L0))
    hook = os.environ.get("DISCORD_WEBHOOK", "")
    if hook:
        try:
            urllib.request.urlopen(urllib.request.Request(hook, data=json.dumps({"content": "\n".join(L0)[:1900]}).encode(),
                                   headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=15)
        except Exception as e:
            print("discord:", e)
    raise SystemExit

n = len(dec); w = sum(1 for r in dec if r["result"] == "WIN"); net = sum(float(r["pnl"]) for r in dec)
oc = [float(r["odds_clv"]) for r in proven if r.get("odds_clv") not in ("", None)]   # self odds-CLV (weak: 1xbet's own close)
slc = [float(r["sharp_clv"]) for r in proven if r.get("sharp_clv") not in ("", None)]          # line vs Pinnacle (combos incl.)
soc = [float(r["sharp_odds_clv"]) for r in proven if r.get("sharp_odds_clv") not in ("", None)]  # price vs Pinnacle fair (TRUE test)
avg_clv = sum(oc) / len(oc) if oc else 0.0
beat = sum(1 for x in oc if x > 0)
beat_pct = beat / len(oc) if oc else 0
avg_soc = sum(soc) / len(soc) if soc else None        # the headline edge metric once it has coverage

L = []
L.append(f"📊 **WNBA BOT — TRACK RECORD** ({n} settled · PROVEN signals only)")
L.append(f"  Record  : {w}-{n - w}  ({w / n * 100:.0f}% hit)")
L.append(f"  Net P&L : {net:+.2f}u  (ROI {net / n * 100:+.1f}%/bet)")
# CLV PROOF HIERARCHY (study all three): sharp-odds > sharp-line > self-odds
if soc:
    sb = sum(1 for x in soc if x > 0)
    L.append(f"  ★ SHARP ODDS-CLV: {avg_soc * 100:+.1f}% | beat fair {sb}/{len(soc)} ({sb / len(soc) * 100:.0f}%)  ← TRUE edge (vs Pinnacle fair price)")
if slc:
    L.append(f"  SHARP LINE-CLV : {sum(slc) / len(slc):+.2f} pts | n={len(slc)}  ← better number than the sharp")
if oc:
    L.append(f"  self ODDS-CLV  : {avg_clv * 100:+.1f}% | beat {beat}/{len(oc)} ({beat_pct * 100:.0f}%)  (1xbet's own close = weak)")
if exp_dec:                                           # the unproven overs, clearly walled off from the headline
    b = _bucket(exp_dec)
    L.append("  ⚗️ Paper / experimental (UNPROVEN, NOT the record): " + " · ".join(
        f"{k} {ww}/{t} ({p:+.1f}u)" for k, (t, ww, p) in sorted(b.items())))

# VERDICT — CLV is the proof; hit-rate at small n is noise. PREFER the sharp odds-CLV (vs Pinnacle's fair price);
# fall back to the self odds-CLV only while sharp coverage is thin, and say so.
pm, pn, plabel = (avg_soc, len(soc), "SHARP") if (avg_soc is not None and len(soc) >= 10) else (avg_clv, len(oc), "self")
if n < 20 or pn < 10:
    lean = "leaning +" if pm > 0.01 else "leaning −" if pm < -0.01 else "flat"
    src_note = "sharp-CLV thin" if plabel == "self" else f"{plabel} n={pn}"
    verdict = f"⏳ TOO EARLY (n={n}; {src_note}, need ~20-40 ≈ 2wks). CLV {lean} — not yet meaningful."
elif pm > 0.02:
    verdict = f"✅ POSITIVE {plabel} CLV — we're beating the {'sharp fair price' if plabel=='SHARP' else 'close'}. Edge looks REAL — consider scaling."
elif pm < -0.01:
    verdict = f"❌ NEGATIVE {plabel} CLV — the {'sharp' if plabel=='SHARP' else 'market'} beats us. No real edge — kill or rebuild."
else:
    verdict = f"⚠️ NEUTRAL {plabel} CLV — winning on outcomes, not beating the line. Unproven; keep collecting."
L.append(f"  VERDICT : {verdict}")

# by tier + by market
for label, key in [("tier", "tier"), ("market", None)]:
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in dec:
        k = (r["tier"] or "?") if key else f"{r['market']} {r['side']}"
        agg[k][0] += 1; agg[k][1] += r["result"] == "WIN"; agg[k][2] += float(r["pnl"])
    L.append(f"  by {label}: " + " · ".join(f"{k} {ww}/{t} ({p:+.1f}u)" for k, (t, ww, p) in sorted(agg.items())))

def _pc(r, col):                                       # CLV cell: % for odds cols, signed pts for the line col, — when blank
    v = r.get(col)
    if v in ("", None):
        return "—"
    try:
        return f"{float(v):+.1f}" if col == "sharp_clv" else f"{float(v) * 100:+.0f}%"
    except ValueError:
        return "—"


print("\n".join(L))
print("\n  PER-BET (sharp = vs Pinnacle [the real test] · self = vs 1xbet's own close · COLD/SHRINK/STINGY = real money):")
print(f"  {'date':9}{'player':18}{'bet':15}{'signal':19}{'res':5}{'shOdds':>7}{'shLine':>7}{'self':>6}")
for r in sorted(rows, key=lambda r: (r["date"], r["player"])):
    print(f"  {r['date']:9}{r['player'][:17]:18}{(r['market'].upper() + ' ' + r['side'])[:14]:15}{lab(_src(r)):19}"
          f"{r['result'][:4]:5}{_pc(r, 'sharp_odds_clv'):>7}{_pc(r, 'sharp_clv'):>7}{_pc(r, 'odds_clv'):>6}")

# persist a human-readable history file (always current; graded_bets.csv = the raw append-only data)
hist = ["# WNBA Bot — CLV & Track Record", "",
        "_Auto-updated after each slate settles. Raw data: `graded_bets.csv`. CLV>0 = we got the better number/price._",
        "_**sharp-odds** = vs Pinnacle's vig-free fair price (TRUE edge test) · **sharp-line** = pts vs Pinnacle's line · "
        "**self** = vs 1xbet's own close (weak)._", "", "```"]
hist += [ln.replace("**", "") for ln in L]
hist += ["```", "", "## Per-bet", "",
         "_signal: **COLD/SHRINK/STINGY** = real money (headline) · everything else = paper/experimental (not in record)_", "",
         "| date | player | bet | signal | result | sharp-odds | sharp-line | self-CLV |",
         "|---|---|---|---|---|---|---|---|"]
for r in sorted(rows, key=lambda x: (x["date"], x["player"])):
    hist.append(f"| {r['date']} | {r['player']} | {r['market'].upper()} {r['side']} {r['line']} @ {r['odds']} | "
                f"{lab(_src(r))} | {r['result']} | {_pc(r, 'sharp_odds_clv')} | {_pc(r, 'sharp_clv')} | {_pc(r, 'odds_clv')} |")
with open("CLV_HISTORY.md", "w", encoding="utf-8") as f:
    f.write("\n".join(hist) + "\n")
print("\n  → wrote CLV_HISTORY.md (check it anytime, on GitHub or locally)")

hook = os.environ.get("DISCORD_WEBHOOK", "")
if hook:
    try:
        urllib.request.urlopen(urllib.request.Request(hook, data=json.dumps({"content": "\n".join(L)[:1900]}).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=15)
        print("\n  (pinged Discord)")
    except Exception as e:
        print("\n  discord:", e)
