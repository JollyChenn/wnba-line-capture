# rolelib.py - shared loader + stats helpers for the ROLE / USAGE MISPRICING track.
# Read-only: touches nothing in the live pipeline, writes nothing.
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO not in sys.path: sys.path.insert(0, REPO)

def boot():
    """exec mega_sweep's preamble with __file__ pointed at the repo root, return its namespace."""
    src = open(os.path.join(REPO, "mega_sweep.py"), encoding="utf-8").read()
    src = src.split('print(f"{len(B)} two-sided board quotes')[0]
    g = {"__name__": "_ms", "__file__": os.path.join(REPO, "mega_sweep.py"), "__builtins__": __builtins__}
    exec(compile(src, os.path.join(REPO, "mega_sweep.py"), "exec"), g)
    return g

# ---------- economics ----------
def am(p):
    try: v = float(p)
    except Exception: return None
    return (-v)/((-v)+100) if v < 0 else 100/(v+100)

def dec(o):
    """board odds are already DECIMAL (e.g. 1.90). profit on a 1u win = o-1."""
    return float(o)

def pnl(odds, won):
    return (dec(odds) - 1.0) if won else -1.0

# ---------- block bootstrap ----------
def block_boot(units, n=4000, rng=None):
    """units = list of lists of per-bet pnl, one inner list per INDEPENDENT unit.
    returns (roi, lo, hi) as percents on a 1u flat stake."""
    rng = rng or random.Random(7)
    flat = [p for u in units for p in u]
    if not flat: return (0.0, 0.0, 0.0)
    roi = 100.0*sum(flat)/len(flat)
    k = len(units); out = []
    for _ in range(n):
        s = 0.0; c = 0
        for _ in range(k):
            u = units[rng.randrange(k)]
            s += sum(u); c += len(u)
        if c: out.append(100.0*s/c)
    out.sort()
    return (roi, out[int(0.025*len(out))], out[int(0.975*len(out))])

def wilson(k, n, z=1.96):
    if n == 0: return (0.0, 0.0, 0.0)
    p = k/n; d = 1+z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return (100*p, 100*(c-h), 100*(c+h))

def fmt_ci(lo, hi):
    return "[%+.1f, %+.1f]" % (lo, hi)
