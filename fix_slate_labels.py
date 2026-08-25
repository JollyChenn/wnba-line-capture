# fix_slate_labels.py - relabel rows written with the old UTC-based slate key.
# ---------------------------------------------------------------------------------------------
# model_card / shadow_log used to name a slate by the UTC date of its earliest tip. That matches
# ESPN only when the night contains a game before midnight UTC. On 2026-08-24 (GS@MIN 00:00Z,
# ATL@LA 02:00Z) the label came out 2026-08-25 while games_2026 dated it 20260824 - and since
# every grader keys on the slate string, those bets could never meet their own box scores.
#
# The writers now derive the label from the Pacific calendar day. This repairs rows already on
# disk by recomputing each row's slate from its OWN tip, so nothing depends on guessing which
# night it belonged to. Idempotent: rows already correct are left untouched.
import csv, os, shutil, sys, datetime
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    TZ = datetime.timezone(datetime.timedelta(hours=-7))
D = os.path.dirname(os.path.abspath(__file__))

def ts(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

for name, dashed in (("model_forward.csv", False), ("shadow_forward.csv", True)):
    path = os.path.join(D, name)
    if not os.path.exists(path): continue
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    if not rows: continue
    changed = 0
    for r in rows:
        t = ts(r.get("tip"))
        if not t: continue
        want = t.astimezone(TZ).strftime("%Y-%m-%d" if dashed else "%Y%m%d")
        if (r.get("slate") or "") != want:
            print(f"  {name}: {r.get('player')} {r.get('market')} {r.get('slate')} -> {want}")
            r["slate"] = want; changed += 1
    if not changed:
        print(f"  {name}: all {len(rows)} slate labels already correct"); continue
    bak = path.replace(".csv", ".pre-slatefix.bak.csv")
    if not os.path.exists(bak): shutil.copy2(path, bak)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)               # atomic
    print(f"  {name}: relabelled {changed} row(s), backup {os.path.basename(bak)}")
