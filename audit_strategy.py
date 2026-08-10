# audit_strategy.py - executable proof that the filter and the strategy do what we claim.
# ---------------------------------------------------------------------------------------------
# Every check here corresponds to something that ACTUALLY BROKE in live running. This is not a
# style review; it is a regression suite for the parts that silently lied to us:
#   - a blind board reading 0.0% and looking like an all-clear
#   - bets pinged for games two days away
#   - a schema change shifting every column right so live bets read as "pulled"
#   - the skip rule firing in the wrong DIRECTION would be invisible in the P&L for weeks
# Run it any time:  python audit_strategy.py
# Exit code is 0 only if every check passes.
import csv, os, sys, json, datetime, math
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import alert_bets as A

FAILS, WARNS = [], []
def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))
    if not ok: FAILS.append(name)
def warn(name, detail): print(f"  WARN  {name}   {detail}"); WARNS.append(name)
def load(p):
    fp = os.path.join(D, p)
    return list(csv.DictReader(open(fp, encoding="utf-8"))) if os.path.exists(fp) else []
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

now = datetime.datetime.now(datetime.timezone.utc)
fresh = (now - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
stale = (now - datetime.timedelta(hours=9)).strftime("%Y-%m-%dT%H:%M:%SZ")
def row(**kw):
    base = dict(src="flip", verdict="BET (steady)", confidence="ok 85%", captures="6",
                span_h="5.0", last_utc=fresh, player="X", market="pts", side="Over",
                line="10.5", now_odds="1.8", move_pct="0.0")
    base.update(kw); return base

print("\n=== 1. guard() rejects exactly what it should (synthetic) ===")
cases = [
    ("retired signal blocked",        row(src="newunder"),                       False),
    ("retired model blocked",         row(src="model"),                          False),
    ("drifted bet blocked",           row(verdict="SKIP-drift"),                 False),
    ("new line with no read blocked", row(confidence="NO READ (new line)"),      False),
    ("single observation blocked",    row(captures="1", span_h="0.0"),           False),
    ("short window blocked",          row(captures="2", span_h="1.0"),           False),
    ("stale read blocked",            row(last_utc=stale),                       False),
    ("good bet passes",               row(),                                     True),
    ("4 checks passes even if short", row(captures="4", span_h="0.5"),           True),
    ("3h span passes on 2 checks",    row(captures="2", span_h="3.5"),           True),
]
for name, r, want in cases:
    got = len(A.guard([r], verbose=False)) == 1
    check(name, got == want, f"(passed={got}, expected={want})")

print("\n=== 2. the skip rule fires in the right DIRECTION ===")
# longer odds = market walked away = SKIP.  shorter = money agrees = BET.
gate = load("drift_gate_today.csv")
wrong_dir = [r for r in gate
             if (f(r.get("move_pct")) or 0) >= 1.0 and not r["verdict"].startswith("SKIP")]
also_wrong = [r for r in gate
              if (f(r.get("move_pct")) or 0) <= -1.0 and not r["verdict"].startswith("BET")]
check("every drift >= +1% is SKIPped", not wrong_dir, f"({len(wrong_dir)} violations)")
check("every drift <= -1% is a BET",   not also_wrong, f"({len(also_wrong)} violations)")
neg = [r for r in gate if (f(r.get("move_pct")) or 0) < 0]
check("shortened bets exist to prove the sign convention is live", bool(neg),
      f"({len(neg)} shortened rows, e.g. {neg[0]['player'] if neg else '-'})")

print("\n=== 3. gate arithmetic recomputed from raw bets_log ===")
# independent recomputation: first vs last captured price at the CURRENT line
bl = load("bets_log.csv")
# Replicate the gate's slate window. Without it this recomputation pulls in captures from PREVIOUS
# slates that happen to share a line, which changes "first" and can flip the sign outright - the
# first version of this check reported Malonga as -3.5% vs +3.2% purely from a stale 08-07 capture.
WANT = {now.strftime("%Y-%m-%d"), (now - datetime.timedelta(hours=7)).strftime("%Y-%m-%d")}
series = {}
for r in bl:
    if r.get("date") not in WANT: continue
    k = (r.get("player"), r.get("market"), r.get("side"))
    series.setdefault(k, []).append((r.get("captured_utc"), f(r.get("line")), f(r.get("odds"))))
bad, checked = [], 0
for g in gate:
    k = (g["player"], g["market"], g["side"])
    ser = sorted(x for x in series.get(k, []) if x[0] and x[2])
    if not ser: continue
    cur = f(g["line"])
    cl = [x for x in ser if x[1] == cur]
    if len(cl) < 2: continue
    exp = round(100 * (cl[-1][2] / cl[0][2] - 1), 1)
    checked += 1
    if abs(exp - (f(g["move_pct"]) or 0)) > 0.15:
        bad.append(f"{g['player']} {g['market']}: gate {g['move_pct']}% vs recomputed {exp}%")
check("move_pct matches an independent recomputation", not bad,
      f"({checked} rows checked" + (f", {len(bad)} mismatched: {bad[:2]}" if bad else ")"))

print("\n=== 4. no look-ahead: reads use only pre-decision data ===")
future = [r for r in gate if r.get("last_utc") and r["last_utc"] > now.strftime("%Y-%m-%dT%H:%M:%SZ")]
check("no capture timestamped in the future", not future, f"({len(future)})")
spanbad = [r for r in gate if (f(r.get("span_h")) or 0) > 0 and int(float(r.get("captures") or 0)) < 2]
check("span>0 implies at least 2 captures", not spanbad, f"({len(spanbad)})")

print("\n=== 5. ping record integrity ===")
pinged = load("pinged_bets.csv")
if pinged:
    cols = list(pinged[0].keys())
    check("header matches PING_COLS", cols == A.PING_COLS,
          "" if cols == A.PING_COLS else f"disk={cols[-3:]} code={A.PING_COLS[-3:]}")
    raw = list(csv.reader(open(os.path.join(D, "pinged_bets.csv"), encoding="utf-8")))
    widths = {len(r) for r in raw[1:]}
    check("every row has the header's width", widths == {len(raw[0])}, f"widths={sorted(widths)}")
    seen, dup = set(), []
    for r in pinged:
        k = (r["date"], r["player"], r["market"], r["side"], r["line"])
        if k in seen: dup.append(k)
        seen.add(k)
    check("no duplicate bet on the same night", not dup, f"({len(dup)} dupes)")
    offmenu = [r for r in pinged if r.get("src") not in A.LIVE]
    check("nothing off-menu was ever pinged", not offmenu, f"({len(offmenu)})")
    badstake = [r for r in pinged
                if (r.get("stake", "").startswith("½")) != (r.get("src") in A.HALF_STAKE)]
    check("half stake applied to cascade and only cascade", not badstake, f"({len(badstake)})")
else:
    warn("ping record", "empty - nothing pinged yet")

print("\n=== 6. period/quarter props cannot leak in ===")
# a 'PTS Over 3.5' on a 15-point scorer is a QUARTER line mis-served under the full-game code
tiny = [r for r in gate if (f(r.get("line")) or 99) < 3 and r.get("market") in ("pts", "pra", "pr", "pa")]
check("no sub-3 lines on full-game markets", not tiny,
      f"({len(tiny)}: {[(r['player'], r['line']) for r in tiny][:3]})")

print("\n=== 7. stage state is coherent ===")
stp = os.path.join(D, "alert_state.json")
if os.path.exists(stp):
    st = json.load(open(stp))
    known = {n for n, _ in A.STAGES} | {"late"}
    check("no unknown stage recorded", set(st.get("done", [])) <= known,
          f"done={st.get('done')}")
    check("sent_full is set once a full list went out",
          bool(st.get("sent_full")) or not st.get("done"),
          f"sent_full={st.get('sent_full')} done={st.get('done')}")
else:
    warn("alert_state.json", "absent - will be created on first send")

print("\n=== 8. the edge the filter claims, recomputed ===")
g = [r for r in load("graded_bets.csv")
     if (r.get("result") or "").upper() in ("WIN", "LOSS") and r.get("src") in A.LIVE]
def roi(rows, close=True):
    out = []
    for r in rows:
        o, clv = f(r.get("odds")), f(r.get("odds_clv"))
        if o is None: continue
        pr = o / (1 + clv) if (close and clv is not None) else o
        out.append((pr - 1) if r["result"].upper() == "WIN" else -1.0)
    if len(out) < 10: return None
    m = sum(out) / len(out); sd = (sum((x - m) ** 2 for x in out) / (len(out) - 1)) ** .5
    return len(out), m * 100, m / (sd / math.sqrt(len(out)))
kept = roi([r for r in g if (f(r.get("odds_clv")) or 0) >= -0.01])
drop = roi([r for r in g if (f(r.get("odds_clv")) or 0) < -0.01])
if kept and drop:
    print(f"        kept    n={kept[0]:<4} ROI={kept[1]:+.1f}%  t={kept[2]:+.2f}")
    print(f"        skipped n={drop[0]:<4} ROI={drop[1]:+.1f}%  t={drop[2]:+.2f}")
    check("skipping still separates winners from losers", kept[1] > drop[1] + 10,
          f"(gap {kept[1]-drop[1]:.1f}pp)")
    if kept[2] < 2.0:
        warn("edge significance", f"t={kept[2]:+.2f} is BELOW 2 - suggestive, not proven. "
                                  f"Forward CLV is still the only thing that can settle this.")

print("\n" + "=" * 70)
if FAILS:
    print(f"  {len(FAILS)} CHECK(S) FAILED: " + ", ".join(FAILS))
else:
    print(f"  ALL CHECKS PASSED" + (f"  ({len(WARNS)} warning(s))" if WARNS else ""))
print("=" * 70)
sys.exit(1 if FAILS else 0)
