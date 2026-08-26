# Track 1 step 1: full CSV enumeration -> data dictionary
import csv, os, sys, math, re, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
ROOT = r"C:\Users\Axioo\wnba-line-capture"
OUT  = os.path.join(ROOT, "outputs", "tables")
os.makedirs(OUT, exist_ok=True)

DIRS = [("", ROOT), ("data/", os.path.join(ROOT,"data")), ("elo_model/", os.path.join(ROOT,"elo_model"))]
files=[]
for pre,d in DIRS:
    if not os.path.isdir(d): continue
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".csv"): files.append((pre+fn, os.path.join(d,fn)))

INT=re.compile(r"^-?\d+$"); FLT=re.compile(r"^-?\d*\.\d+([eE][+-]?\d+)?$")
DTP=[re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"), re.compile(r"^\d{4}-\d{2}-\d{2}$"), re.compile(r"^\d{8}$")]
def dtype(vals):
    v=[x for x in vals if x not in ("","NA","None","nan")]
    if not v: return "empty"
    if all(DTP[0].match(x) for x in v): return "datetime"
    if all(DTP[1].match(x) for x in v): return "date(YYYY-MM-DD)"
    if all(DTP[2].match(x) for x in v): return "date(YYYYMMDD)"
    if all(INT.match(x) for x in v): return "int"
    if all(INT.match(x) or FLT.match(x) for x in v): return "float"
    if set(x.lower() for x in v)<= {"true","false","0","1","win","loss"}: return "bool/enum"
    return "str"

def find_date(hdr, rows):
    # best-effort date range: first column whose dtype is date/datetime
    for c in hdr:
        vals=[r.get(c,"") for r in rows[:400]]
        t=dtype(vals)
        if t.startswith("date") or t=="datetime":
            allv=sorted(set(x for x in (r.get(c,"") for r in rows) if x and x not in ("NA","None")))
            if allv: return c, allv[0][:19], allv[-1][:19]
    return None,None,None

lines=["# WNBA line-capture -- DATA DICTIONARY","",
       f"Generated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} by outputs/t1_enum.py (read-only audit).",
       "",
       "Scope: every `.csv` in repo root, `data/`, `elo_model/`. `.bak.csv` / `pre-*` files are prior-state",
       "backups kept by the pipeline and are flagged as such -- they are NOT independent data.","",
       "| file | rows | cols | date col | date range |","|---|---|---|---|---|"]
detail=[]
summary={}
for rel,path in files:
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd=csv.reader(fh)
        try: hdr=next(rd)
        except StopIteration: hdr=[]
        rows=[]
        for row in rd:
            if len(row)<len(hdr): row=row+[""]*(len(hdr)-len(row))
            rows.append(dict(zip(hdr,row[:len(hdr)])))
    n=len(rows)
    dc,d0,d1=find_date(hdr,rows) if n else (None,None,None)
    bak = ".bak." in rel or ".pre-" in rel or "backup" in rel or "corrupt" in rel
    summary[rel]=dict(n=n,cols=hdr,dc=dc,d0=d0,d1=d1,bak=bak)
    lines.append(f"| `{rel}`{' (BACKUP)' if bak else ''} | {n:,} | {len(hdr)} | {dc or '-'} | {(d0+' .. '+d1) if d0 else '-'} |")
    # detail block
    detail.append(f"\n### `{rel}`\n")
    if bak: detail.append("_Backup/prior-state file - not independent data._\n")
    detail.append(f"Rows: **{n:,}**  Columns: **{len(hdr)}**"+(f"  Date range (`{dc}`): **{d0} .. {d1}**" if d0 else "")+"\n")
    detail.append("| column | dtype | non-null | distinct | example |")
    detail.append("|---|---|---|---|---|")
    for c in hdr:
        vals=[r.get(c,"") for r in rows]
        nn=sum(1 for x in vals if x not in ("","NA","None"))
        dis=len(set(vals))
        ex=next((x for x in vals if x not in ("","NA","None")),"")
        ex=(ex[:40]+"...") if len(ex)>40 else ex
        detail.append(f"| {c} | {dtype(vals)} | {nn:,} ({(100*nn/n if n else 0):.0f}%) | {dis:,} | `{ex}` |")
    if rows:
        s=rows[0]
        detail.append("\nSample row:\n\n```\n"+", ".join(f"{k}={s.get(k,'')!r}" for k in hdr)+"\n```")

open(os.path.join(OUT,"data_dictionary.md"),"w",encoding="utf-8").write(
    "\n".join(lines)+"\n\n---\n\n## Per-file detail\n"+"\n".join(detail)+"\n")
print("files:",len(files),"total rows:",sum(v['n'] for v in summary.values()))
for rel,v in summary.items():
    if not v["bak"]: print(f"  {rel:48s} {v['n']:>9,}  {v['d0']} .. {v['d1']}")
