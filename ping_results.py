# ping_results.py - NOTIFICATION 2 OF 2. The morning result of last night's card.
# ---------------------------------------------------------------------------------------------
# THE WHOLE NOTIFICATION POLICY LIVES IN TWO FILES AND NOWHERE ELSE:
#
#   1. model_card.py    evening  - "here are tonight's bets"   (silent when there are none)
#   2. ping_results.py  morning  - "here is how they did"      (silent when nothing settled)
#
# Every other script is muted. health_check.py used to fire its own alerts; it now prints to the
# log instead, because a bot-plumbing warning at 04:00 is not a betting decision and it trains
# you to swipe the channel away - which is exactly when you miss the card that matters.
#
# Idempotent: it keys on the slate it just reported and will not repeat it. run_grade.py calls
# this every 2 hours; you get the message once, on the first run after the last game settles.
import csv, os, sys, json, datetime, collections, urllib.request
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
FWD  = os.path.join(D, "model_forward.csv")
SENT = os.path.join(D, "results_sent.json")

def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8", errors="replace"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def send(msg):
    p = os.path.join(D, "webhook.txt")
    wh = open(p).read().strip() if os.path.exists(p) else ""
    if not wh:
        print("[no webhook - results printed only]"); return False
    try:
        urllib.request.urlopen(urllib.request.Request(
            wh, data=json.dumps({"content": msg[:1900]}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "wnba-bot"}), timeout=15)
        return True
    except Exception as e:
        print("  discord failed:", e); return False

rows = load("model_forward.csv")
if not rows:
    print("  no forward record yet"); raise SystemExit

def done(r): return (r.get("result") or "").upper() in ("WIN", "LOSS", "PUSH")

# ---- which slate do we report? the newest one that is COMPLETELY settled --------------------------
by_slate = collections.defaultdict(list)
for r in rows: by_slate[r.get("slate") or ""].append(r)
finished = sorted(s for s, v in by_slate.items() if s and all(done(r) for r in v))
if not finished:
    print("  newest slate still has ungraded bets - waiting"); raise SystemExit
slate = finished[-1]

sent = json.load(open(SENT)) if os.path.exists(SENT) else {}
if sent.get("last") == slate:
    print(f"  already reported {slate}"); raise SystemExit

# ---- that night ----------------------------------------------------------------------------------
night = by_slate[slate]
def pnl(r):
    res = (r.get("result") or "").upper()
    if res == "PUSH": return 0.0
    o = f(r.get("odds")) or 1.9
    return (o - 1) if res == "WIN" else -1.0
nw = sum(1 for r in night if (r.get("result") or "").upper() == "WIN")
nl = sum(1 for r in night if (r.get("result") or "").upper() == "LOSS")
nu = sum(pnl(r) for r in night)

# ---- the running record, which is the number that actually decides anything ----------------------
allg = [r for r in rows if done(r)]
aw = sum(1 for r in allg if (r.get("result") or "").upper() == "WIN")
al = sum(1 for r in allg if (r.get("result") or "").upper() == "LOSS")
au = sum(pnl(r) for r in allg)
roi = 100 * au / len(allg) if allg else 0.0

head = "🟢" if nu > 0 else ("🔴" if nu < 0 else "⚪")
lines = [f"{head} **MODEL S RESULT · {slate}** · {nw}-{nl} · {nu:+.2f}u"]
for r in night:
    res = (r.get("result") or "").upper()
    mark = {"WIN": "✅", "LOSS": "❌", "PUSH": "➖"}.get(res, "·")
    act = r.get("actual") or "?"
    lines.append(f"{mark} {r.get('player')} {(r.get('market') or '').upper()} "
                 f"Over {r.get('line')} @ {r.get('odds')} — got {act}")
lines.append(f"_forward record: {aw}-{al} · {au:+.2f}u · ROI {roi:+.1f}% "
             f"over {len(allg)} bets · reviewing at 50_")
msg = "\n".join(lines)
print("\n" + msg + "\n")

if send(msg):
    print("pinged Discord")
    sent["last"] = slate
    tmp = SENT + ".tmp"
    json.dump(sent, open(tmp, "w")); os.replace(tmp, SENT)     # atomic, never a half-written file
