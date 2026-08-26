# shared preamble loader for outputs/hyp studies (read-only on the pipeline)
import csv, os, sys, math, random, statistics, datetime, collections
def boot(g):
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if ROOT not in sys.path: sys.path.insert(0, ROOT)
    src = open(os.path.join(ROOT, "mega_sweep.py"), encoding="utf-8").read()
    src = src.split('print(f"{len(B)} two-sided board quotes')[0]
    g["__file__"] = os.path.join(ROOT, "mega_sweep.py")   # so mega_sweep's own D resolves to root
    exec(compile(src, "mega_sweep.py", "exec"), g)
    g["ROOT"] = ROOT
    return ROOT
