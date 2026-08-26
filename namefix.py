# namefix.py - resolve 1xbet board player names to box-score names.
# ---------------------------------------------------------------------------------------------
# The board-to-box join was an exact lowercase string match. It failed on 8 names covering 3,201
# board rows (3.9% of the prop book) - and every one is a real rostered player, led by A'ja Wilson
# at 1,530 rows. So every study that joined the board to the box silently deleted the league's
# highest-usage player, and the live model cannot bet her at all. A silent drop of the biggest
# name in the league is the worst kind of data bug: it never errors, and it biases exactly the
# population ("stars", "usage rank") that people most want to draw conclusions about.
#
# Resolution ladder, cheapest first. Each rung is deterministic and reversible:
#   1 NORMALISE both sides: accent-fold, strip apostrophes/hyphens/periods, collapse spaces.
#     ("A'ja Wilson" -> "aja wilson")
#   2 EXACT normalised match.
#   3 REVERSED token order.            ("xu han" -> "Han Xu")
#   4 TOKEN SUBSET either way, so middle names and appended surnames resolve.
#     ("janelle illona salaun" -> "Janelle Salaun"; "cheyenne parker" -> "Cheyenne Parker-Tyus")
#   5 SURNAME + first-name-prefix.     ("nazahrah hillmon baker" -> "Naz Hillmon")
#   6 CURATED ALIASES for the genuinely different names - a nickname or a changed surname cannot
#     be derived by any rule and must be written down.
# Anything still unresolved is returned as None and SHOULD be logged loudly by the caller.
import csv, os, re, unicodedata, collections

ALIASES = {                      # board spelling -> box spelling, normalised on both sides
    "alexa held": "lexi held",                       # nickname
    "valeriane vukosavljevic": "valeriane ayayi",    # surname change
    "awa fam thiam": "awa fam",                      # appended surname (also caught by rung 4)
    "nazahrah hillmon baker": "naz hillmon",         # nickname + hyphenated surname
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = s.replace("-", " ").replace(".", " ").replace("'", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", s)).strip()

def build(box_path):
    """box name index -> resolver function. Call once, reuse."""
    names = set()
    for r in csv.DictReader(open(box_path, encoding="utf-8", errors="replace")):
        p = (r.get("player") or "").strip()
        if p: names.add(p)
    exact, rev, toks = {}, {}, {}
    for b in names:
        n = norm(b)
        exact.setdefault(n, b)
        t = n.split()
        if len(t) >= 2: rev.setdefault(" ".join(reversed(t)), b)
        toks[b] = set(t)
    def resolve(board_name):
        n = norm(board_name)
        if not n: return None
        if n in exact: return exact[n]
        if n in rev: return rev[n]
        a = ALIASES.get(n)
        if a and a in exact: return exact[a]
        bt = set(n.split())
        # token subset either direction (middle names, appended surnames)
        cands = [b for b, t in toks.items() if t and (t <= bt or bt <= t)]
        if len(cands) == 1: return cands[0]
        # surname match + first-name prefix either direction
        if len(bt) >= 2:
            last = n.split()[-1]; first = n.split()[0]
            cands = [b for b, t in toks.items()
                     if last in t and any(x.startswith(first[:3]) or first.startswith(x[:3]) for x in t)]
            if len(cands) == 1: return cands[0]
        return None
    return resolve

if __name__ == "__main__":
    D = os.path.dirname(os.path.abspath(__file__))
    resolve = build(os.path.join(D, "data", "box_2026.csv"))
    box = {(r.get("player") or "").strip().lower()
           for r in csv.DictReader(open(os.path.join(D, "data", "box_2026.csv"), encoding="utf-8"))}
    cnt = collections.Counter()
    for b in csv.DictReader(open(os.path.join(D, "xbet_board.csv"), encoding="utf-8", errors="replace")):
        p = (b.get("player") or "").strip()
        if p and p.lower() not in box: cnt[p] += 1
    ok = bad = 0
    for k, v in cnt.most_common():
        hit = resolve(k)
        print(f"  {k:<30} -> {hit if hit else '*** UNRESOLVED ***':<30} {v:>5} rows")
        if hit: ok += v
        else: bad += v
    print(f"\n  recovered {ok} rows across {len(cnt)} names; still unresolved {bad}")
