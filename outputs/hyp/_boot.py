# shared bootstrap: exec mega_sweep's data layer with D pinned to the REPO ROOT
import csv, os, sys, math, random, statistics, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_src = open(os.path.join(ROOT, "mega_sweep.py"), encoding="utf-8").read() \
        .split('print(f"{len(B)} two-sided board quotes')[0]
_src = _src.replace('D = os.path.dirname(os.path.abspath(__file__))', 'D = ROOT')
