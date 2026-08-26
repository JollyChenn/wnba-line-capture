# gm_build_dataset.py - TRACK 0: build the game-market analysis dataset + baselines.
# READ-ONLY on everything else. Writes ONLY outputs/gm/*.
import os, sys, math, json
import numpy as np, pandas as pd
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

ROOT = r"C:\Users\Axioo\wnba-line-capture"
E    = os.path.join(ROOT, "elo_model")
OUT  = os.path.join(ROOT, "outputs", "gm")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20260826)
pd.set_option("display.width", 200)

def P(*a): print(*a, flush=True)
def H(t): P("\n" + "=" * 78); P(t); P("=" * 78)

# ----------------------------------------------------------------- load raw
be = pd.read_csv(os.path.join(E, "be_odds.csv"), dtype=str)
gf = pd.read_csv(os.path.join(E, "games_full.csv"), dtype=str)
fv = pd.read_csv(os.path.join(E, "feats_v5.csv"))
for c in be.columns: be[c] = be[c].astype(str).str.strip()
for c in gf.columns: gf[c] = gf[c].astype(str).str.strip()
NUM_BE = ["hscore","ascore","ml_h","ml_a","spread","sp_h","sp_a","total","ou_o","ou_u","n_bk_sp","n_bk_ou"]
for c in NUM_BE: be[c] = pd.to_numeric(be[c], errors="coerce")
for c in ["home_score","away_score"]: gf[c] = pd.to_numeric(gf[c], errors="coerce")

H("RAW SHAPES")
P(f"be_odds    {be.shape}")
P(f"games_full {gf.shape}")
P(f"feats_v5   {fv.shape}  seasons {sorted(fv.season.unique())}")
P("\nbe_odds column completeness:")
for c in NUM_BE: P(f"   {c:8} non-null {be[c].notna().sum():5d} / {len(be)}")

# ------------------------------------------------------- 1. slug -> (H,A)
NICK = {"atlanta-dream":"ATL","chicago-sky":"CHI","connecticut-sun":"CON","dallas-wings":"DAL",
        "indiana-fever":"IND","las-vegas-aces":"LV","los-angeles-sparks":"LA","minnesota-lynx":"MIN",
        "new-york-liberty":"NY","phoenix-mercury":"PHX","seattle-storm":"SEA","washington-mystics":"WSH",
        "golden-state-valkyries":"GS","portland-fire":"POR","toronto-tempo":"TOR"}
pref_clash = [(a, b) for a in NICK for b in NICK if a != b and b.startswith(a)]
P(f"\nteam-slug prefix clashes: {pref_clash}   (empty list => prefix parse is unambiguous)")

def parse_slug(s):
    for k in NICK:
        if s.startswith(k + "-"):
            rest = s[len(k) + 1:]
            if rest in NICK:
                return NICK[k], NICK[rest]      # slug is HOME-AWAY
    return None, None

be[["home", "away"]] = be.slug.apply(lambda s: pd.Series(parse_slug(s), index=["home", "away"]))
bad = be[be.home.isna()]
H("1. SLUG PARSE")
P(f"parsed {len(be)-len(bad)}/{len(be)}  ({100*(len(be)-len(bad))/len(be):.1f}%)")
P("unparsed slugs -> EXCLUDED (all-star / exhibition, not WNBA team games):")
for s, n in bad.slug.value_counts().items(): P(f"   {n:3d}  {s}")
be = be[be.home.notna()].copy()

# ------------------------------------------------- 1b. join to games_full
ALLSTAR = {"CLA", "COOP", "WIL", "WNBASTARS"}
gf_use = gf[(~gf.home.isin(ALLSTAR)) & (~gf.away.isin(ALLSTAR)) & gf.home_score.notna()].copy()
P(f"\ngames_full usable (all-star teams dropped, final score present): {len(gf_use)}")

idx = {}
for r in gf_use.itertuples():
    idx.setdefault((r.season, r.home, r.away), []).append(r)
dup_matchup = sum(1 for v in idx.values() if len(v) > 1)
P(f"(season,home,away) keys with >1 game: {dup_matchup} -> score is needed to disambiguate")

taken, rec, fail = set(), [], []
cnt = dict(uniq=0, multi=0, nocand=0, mismatch=0, ambig=0, dupe=0)
for r in be.itertuples():
    cand = idx.get((r.season, r.home, r.away), [])
    if not cand:
        cnt["nocand"] += 1; fail.append((r.season, r.slug, "no (season,home,away) key in games_full")); rec.append(None); continue
    cnt["uniq" if len(cand) == 1 else "multi"] += 1
    scored = [c for c in cand if c.home_score == r.hscore and c.away_score == r.ascore]
    free = [c for c in scored if c.game_id not in taken]
    if not scored:
        cnt["mismatch"] += 1
        fail.append((r.season, r.slug, f"SCORE DISAGREE be({int(r.hscore)}-{int(r.ascore)}) vs gf{[(int(c.home_score),int(c.away_score)) for c in cand]}"))
        rec.append(None); continue
    if not free:
        cnt["dupe"] += 1; fail.append((r.season, r.slug, "duplicate odds row: matching game already claimed")); rec.append(None); continue
    if len(free) > 1: cnt["ambig"] += 1
    c = sorted(free, key=lambda x: x.date)[0]
    taken.add(c.game_id); rec.append((c.game_id, c.date))

be["game_id"] = [x[0] if x else None for x in rec]

H("1b. JOIN be_odds -> games_full   key=(season,home,away) disambiguated by final score")
P(f"parsed odds rows              : {len(be)}")
P(f"  unique-candidate keys       : {cnt['uniq']}")
P(f"  multi-candidate keys        : {cnt['multi']}  (resolved by score)")
P(f"MATCHED                       : {be.game_id.notna().sum()}  ({100*be.game_id.notna().mean():.1f}%)")
P(f"  EXCLUDED no candidate       : {cnt['nocand']}")
P(f"  EXCLUDED SCORE DISAGREE     : {cnt['mismatch']}   <-- suspect rows, dropped")
P(f"  EXCLUDED duplicate odds row : {cnt['dupe']}")
P(f"  (matched but >1 identical-score candidate, took earliest: {cnt['ambig']})")
P("\nfailure detail (up to 40):")
for s in fail[:40]: P("   ", s)

D = be[be.game_id.notna()].copy()
D = D.merge(gf_use[["game_id", "date", "home_score", "away_score"]], on="game_id", how="left")
assert (D.hscore == D.home_score).all() and (D.ascore == D.away_score).all()
assert D.game_id.is_unique
P(f"\nkept: {len(D)} rows, unique game_id, score agreement 100% by construction")

# ---------------------------------------------------------- 2. feats_v5 join
fv["game_id"] = fv.game_id.astype(str).str.strip()
D["game_id"] = D.game_id.astype(str).str.strip()
fv2 = fv.rename(columns={"margin": "f_margin", "total": "f_total"}).drop(columns=["season"])
FEATS = [c for c in fv2.columns if c != "game_id"]
D = D.merge(fv2, on="game_id", how="left")
H("2. feats_v5 JOIN")
P(f"feats_v5 rows {len(fv)}; joined onto {D.f_margin.notna().sum()} of {len(D)} odds games")
P(D.groupby("season").agg(games=("game_id", "size"), with_feats=("f_margin", "count")).to_string())

# --------------------------------------------------------- 3. outcomes
D["home_margin"] = D.home_score - D.away_score
D["game_total"] = D.home_score + D.away_score
D["home_won"] = (D.home_margin > 0).astype(int)
P(f"\nties (home_margin == 0): {(D.home_margin == 0).sum()}  (WNBA plays OT, expect 0)")

def cover_state(m, sp):
    if pd.isna(sp): return np.nan
    v = m + sp
    return 1.0 if v > 0 else (0.0 if v < 0 else 0.5)     # 0.5 == PUSH
def ou_state(t, ln):
    if pd.isna(ln): return np.nan
    return 1.0 if t > ln else (0.0 if t < ln else 0.5)   # 0.5 == PUSH
D["home_covered"] = [cover_state(m, s) for m, s in zip(D.home_margin, D.spread)]
D["over_hit"] = [ou_state(t, l) for t, l in zip(D.game_total, D.total)]

# ------------------------------------------- 4. FEATURE AUDIT (leak test)
H("4. FEATURE AUDIT - is each feats_v5 column knowable PRE-GAME?")
F = D[D.f_margin.notna()].copy()
F["mkt_margin"] = -F.spread          # market's expected home margin (home spread is negative when favoured)
F["ats_resid"] = F.home_margin - F.mkt_margin
F["tot_resid"] = F.game_total - F.total
P(f"audit sample: {len(F)} games that have BOTH feats_v5 and closing odds\n")

P("--- A. are feats_v5 'margin'/'total' the MARKET LINE or the REALISED RESULT? ---")
P(f"  corr(f_margin, REALISED home_margin) = {F.f_margin.corr(F.home_margin):+.4f}"
  f"   mean|diff|={(F.f_margin-F.home_margin).abs().mean():7.3f}   exact-equal={(F.f_margin==F.home_margin).mean()*100:5.1f}%")
P(f"  corr(f_margin, MARKET  -spread     ) = {F.f_margin.corr(F.mkt_margin):+.4f}"
  f"   mean|diff|={(F.f_margin-F.mkt_margin).abs().mean():7.3f}   exact-equal={(F.f_margin==F.mkt_margin).mean()*100:5.1f}%")
P(f"  corr(f_total , REALISED game_total ) = {F.f_total.corr(F.game_total):+.4f}"
  f"   mean|diff|={(F.f_total-F.game_total).abs().mean():7.3f}   exact-equal={(F.f_total==F.game_total).mean()*100:5.1f}%")
P(f"  corr(f_total , MARKET  total line  ) = {F.f_total.corr(F.total):+.4f}"
  f"   mean|diff|={(F.f_total-F.total).abs().mean():7.3f}   exact-equal={(F.f_total==F.total).mean()*100:5.1f}%")
P("  --> VERDICT printed in the audit table below.")

def tstat(r, n):
    if n < 5 or abs(r) >= 1: return float("nan")
    return r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))

H("4b. PER-FEATURE LEAK TABLE")
P("r_out  = corr(feature, realised home_margin)        [what it 'knows' about the result]")
P("r_mkt  = corr(feature, market -spread)              [what a 10-book close already knows]")
P("r_ats  = corr(feature, home_margin - market margin) [what it knows BEYOND the close]  t = its t-stat")
P("r_totO = corr(feature, realised total) ; r_totM = corr(feature, market total line)")
P("LEAK RULE: a pre-game feature cannot know the result better than the closing line does.")
P("  flag if |r_out| > |r_mkt| + 0.15  AND |r_out| > 0.5   ->  DISQUALIFY as post-game.")
P("")
hdr = f"{'feature':10} {'nonnull':>7} {'sd':>8} {'r_out':>7} {'r_mkt':>7} {'r_ats':>7} {'t_ats':>6} {'r_totO':>7} {'r_totM':>7}  verdict"
P(hdr); P("-" * len(hdr))
audit_rows, KEEP, DROP = [], [], []
n = len(F)
for c in FEATS:
    x = pd.to_numeric(F[c], errors="coerce")
    sd = float(x.std())
    r_out = float(x.corr(F.home_margin)) if sd > 0 else float("nan")
    r_mkt = float(x.corr(F.mkt_margin)) if sd > 0 else float("nan")
    r_ats = float(x.corr(F.ats_resid)) if sd > 0 else float("nan")
    r_to = float(x.corr(F.game_total)) if sd > 0 else float("nan")
    r_tm = float(x.corr(F.total)) if sd > 0 else float("nan")
    leak = (not math.isnan(r_out)) and abs(r_out) > abs(r_mkt) + 0.15 and abs(r_out) > 0.5
    # total-side leak: knows realised total far better than the total line does
    leak_t = (not math.isnan(r_to)) and abs(r_to) > abs(r_tm) + 0.15 and abs(r_to) > 0.5
    if sd == 0 or math.isnan(sd):
        v = "DROP: constant"; DROP.append((c, v))
    elif leak or leak_t:
        v = "DISQUALIFY: POST-GAME LEAK"; DROP.append((c, v))
    else:
        v = "keep"; KEEP.append(c)
    audit_rows.append(dict(feature=c, nonnull=int(x.notna().sum()), sd=sd, r_out=r_out, r_mkt=r_mkt,
                           r_ats=r_ats, t_ats=tstat(r_ats, n), r_totO=r_to, r_totM=r_tm, verdict=v))
    P(f"{c:10} {int(x.notna().sum()):7d} {sd:8.3f} {r_out:+7.3f} {r_mkt:+7.3f} {r_ats:+7.3f} "
      f"{tstat(r_ats, n):+6.2f} {r_to:+7.3f} {r_tm:+7.3f}  {v}")
pd.DataFrame(audit_rows).to_csv(os.path.join(OUT, "gm_feature_audit.csv"), index=False)
P(f"\nKEEP ({len(KEEP)}): {KEEP}")
P(f"DROP ({len(DROP)}): {DROP}")

# extra evidence on the two suspicious columns
H("4c. EXTRA EVIDENCE ON f_margin / f_total")
sub = F[["home","away","season","spread","total","home_margin","game_total","f_margin","f_total"]].head(12)
P(sub.to_string(index=False))
P("\nIf f_margin were the LINE it would equal -spread and be a half-integer; if it is the RESULT it equals home_margin.")
P(f"f_margin is integer-valued on {(F.f_margin == F.f_margin.round()).mean()*100:.1f}% of rows; "
  f"-spread is integer-valued on {(F.mkt_margin == F.mkt_margin.round()).mean()*100:.1f}%")
P(f"f_total  is integer-valued on {(F.f_total == F.f_total.round()).mean()*100:.1f}% of rows; "
  f"total line is integer-valued on {(F.total == F.total.round()).mean()*100:.1f}%")

# ---------------------------------------------------------- 3b. write dataset
BASE = ["game_id","date","season","home","away","home_score","away_score",
        "ml_h","ml_a","spread","sp_h","sp_a","total","ou_o","ou_u","n_bk_sp","n_bk_ou",
        "home_margin","game_total","home_won","home_covered","over_hit"]
OUTCOLS = BASE + KEEP
DS = D[OUTCOLS].sort_values(["date","game_id"]).reset_index(drop=True)
path = os.path.join(OUT, "gm_dataset.csv")
DS.to_csv(path, index=False)
H("3. DATASET WRITTEN")
P(f"{path}   rows={len(DS)} cols={len(DS.columns)}")
P(f"columns: {list(DS.columns)}")
P(f"\nrows fully priced (ml+spread+total all present): "
  f"{DS[['ml_h','ml_a','sp_h','sp_a','ou_o','ou_u','spread','total']].notna().all(axis=1).sum()}")

# ---------------------------------------------------------- 5/6. BASELINES
H("6. PUSH RATES")
sp_ok = DS.home_covered.notna()
ou_ok = DS.over_hit.notna()
P(f"spread: n={int(sp_ok.sum())}  pushes={(DS.home_covered==0.5).sum()}  ({100*(DS.home_covered[sp_ok]==0.5).mean():.2f}%)")
P(f"total : n={int(ou_ok.sum())}  pushes={(DS.over_hit==0.5).sum()}  ({100*(DS.over_hit[ou_ok]==0.5).mean():.2f}%)")
P("integer spread lines: %.1f%%   integer total lines: %.1f%%" %
  (100*(DS.spread.dropna() == DS.spread.dropna().round()).mean(),
   100*(DS.total.dropna() == DS.total.dropna().round()).mean()))

def pnl_series(df, kind):
    """return per-game profit in units for a blind strategy; NaN where unavailable. Push -> 0."""
    o = np.full(len(df), np.nan)
    if kind == "home_ml":
        m = df.ml_h.notna()
        o[m.values] = np.where(df.home_won[m] == 1, df.ml_h[m] - 1, -1)
    elif kind == "away_ml":
        m = df.ml_a.notna()
        o[m.values] = np.where(df.home_won[m] == 0, df.ml_a[m] - 1, -1)
    elif kind in ("fav_ml", "dog_ml"):
        m = df.ml_h.notna() & df.ml_a.notna() & (df.ml_h != df.ml_a)
        d = df[m]
        home_is_fav = d.ml_h < d.ml_a
        take_home = home_is_fav if kind == "fav_ml" else ~home_is_fav
        price = np.where(take_home, d.ml_h, d.ml_a)
        win = np.where(take_home, d.home_won == 1, d.home_won == 0)
        o[m.values] = np.where(win, price - 1, -1)
    elif kind == "over":
        m = df.ou_o.notna() & df.over_hit.notna()
        d = df[m]
        o[m.values] = np.where(d.over_hit == 1, d.ou_o - 1, np.where(d.over_hit == 0.5, 0.0, -1))
    elif kind == "under":
        m = df.ou_u.notna() & df.over_hit.notna()
        d = df[m]
        o[m.values] = np.where(d.over_hit == 0, d.ou_u - 1, np.where(d.over_hit == 0.5, 0.0, -1))
    elif kind == "home_spread":
        m = df.sp_h.notna() & df.home_covered.notna()
        d = df[m]
        o[m.values] = np.where(d.home_covered == 1, d.sp_h - 1, np.where(d.home_covered == 0.5, 0.0, -1))
    elif kind == "away_spread":
        m = df.sp_a.notna() & df.home_covered.notna()
        d = df[m]
        o[m.values] = np.where(d.home_covered == 0, d.sp_a - 1, np.where(d.home_covered == 0.5, 0.0, -1))
    elif kind == "fav_spread":
        m = df.sp_h.notna() & df.sp_a.notna() & df.home_covered.notna() & df.spread.notna() & (df.spread != 0)
        d = df[m]
        take_home = d.spread < 0
        price = np.where(take_home, d.sp_h, d.sp_a)
        cov = np.where(take_home, d.home_covered, 1 - d.home_covered)
        o[m.values] = np.where(cov == 1, price - 1, np.where(cov == 0.5, 0.0, -1))
    elif kind == "dog_spread":
        m = df.sp_h.notna() & df.sp_a.notna() & df.home_covered.notna() & df.spread.notna() & (df.spread != 0)
        d = df[m]
        take_home = d.spread > 0
        price = np.where(take_home, d.sp_h, d.sp_a)
        cov = np.where(take_home, d.home_covered, 1 - d.home_covered)
        o[m.values] = np.where(cov == 1, price - 1, np.where(cov == 0.5, 0.0, -1))
    return o

def boot_ci(x, B=4000):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 10: return (float("nan"), float("nan"))
    idx = rng.integers(0, len(x), size=(B, len(x)))
    means = x[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5) * 100), float(np.percentile(means, 97.5) * 100))

STRATS = ["home_ml","away_ml","fav_ml","dog_ml","over","under","home_spread","away_spread","fav_spread","dog_spread"]
H("5. BASELINE - blind strategies at real closing prices (flat 1u, pushes = 0)")
P("overrounds (median across games):")
ov_ml = (1/DS.ml_h + 1/DS.ml_a - 1).dropna()
ov_sp = (1/DS.sp_h + 1/DS.sp_a - 1).dropna()
ov_ou = (1/DS.ou_o + 1/DS.ou_u - 1).dropna()
for nm, s in (("moneyline", ov_ml), ("spread", ov_sp), ("total", ov_ou)):
    P(f"   {nm:10} n={len(s):5d}  median {100*s.median():.2f}%  mean {100*s.mean():.2f}%  "
      f"breakeven on a fair 2-way = {100*(1+s.median())/2:.2f}%")

res = {}
P("\nPOOLED (all seasons):")
P(f"{'strategy':13} {'n':>5} {'hit%':>7} {'ROI%':>8} {'95% CI (game bootstrap)':>28}")
for k in STRATS:
    o = pnl_series(DS, k)
    v = o[~np.isnan(o)]
    if not len(v): continue
    roi = 100 * v.mean()
    lo, hi = boot_ci(v)
    hit = 100 * (v > 0).mean()
    res[k] = dict(n=int(len(v)), roi=roi, ci=[lo, hi], hit=hit)
    P(f"{k:13} {len(v):5d} {hit:7.2f} {roi:+8.2f}   [{lo:+7.2f}, {hi:+7.2f}]")

P("\nBY SEASON (ROI%, n in brackets):")
seasons = sorted(DS.season.unique())
P(f"{'strategy':13}" + "".join(f"{s:>15}" for s in seasons))
for k in STRATS:
    line = f"{k:13}"
    for s in seasons:
        o = pnl_series(DS[DS.season == s], k)
        v = o[~np.isnan(o)]
        line += f"{(100*v.mean() if len(v) else float('nan')):+9.2f}({len(v):3d})" if len(v) else f"{'--':>15}"
    P(line)

P("\nRAW BASE RATES (no price):")
P(f"  home win rate      : {DS.home_won.mean()*100:.2f}%  (n={len(DS)})")
sp = DS[DS.home_covered.notna() & (DS.home_covered != 0.5)]
P(f"  home cover rate    : {(sp.home_covered==1).mean()*100:.2f}%  (n={len(sp)}, pushes excluded)")
ou = DS[DS.over_hit.notna() & (DS.over_hit != 0.5)]
P(f"  over rate          : {(ou.over_hit==1).mean()*100:.2f}%  (n={len(ou)}, pushes excluded)")
fav = DS[DS.ml_h.notna() & DS.ml_a.notna() & (DS.ml_h != DS.ml_a)]
fw = np.where(fav.ml_h < fav.ml_a, fav.home_won == 1, fav.home_won == 0)
P(f"  favourite win rate : {fw.mean()*100:.2f}%  (n={len(fav)})")
P(f"  mean home margin   : {DS.home_margin.mean():+.2f}   mean market home margin: {(-DS.spread).mean():+.2f}")
P(f"  mean game total    : {DS.game_total.mean():.2f}   mean market total       : {DS.total.mean():.2f}")

json.dump(dict(pooled=res,
               overround=dict(ml=float(ov_ml.median()), spread=float(ov_sp.median()), total=float(ov_ou.median())),
               n=len(DS), keep=KEEP, drop=[d[0] for d in DROP]),
          open(os.path.join(OUT, "gm_baseline.json"), "w"), indent=1)
P("\nwrote " + os.path.join(OUT, "gm_baseline.json"))
