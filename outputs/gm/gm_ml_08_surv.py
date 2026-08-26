import pandas as pd, numpy as np
g=pd.read_csv("elo_model/games_full.csv").dropna(subset=["home_score"])
d=pd.read_csv("outputs/gm/gm_ml_base.csv")
g["priced"]=g.game_id.isin(d.game_id)
g["hw"]=(g.home_score>g.away_score).astype(int)
print(g.groupby(["season","priced"]).agg(n=("hw","size"),homewin=("hw","mean")).unstack(fill_value=0))
print("\nOverall priced n=%d homewin=%.4f | unpriced n=%d homewin=%.4f"%(
 g.priced.sum(),g.hw[g.priced].mean(),(~g.priced).sum(),g.hw[~g.priced].mean()))
from scipy import stats
print("chi2 p =", stats.chi2_contingency(pd.crosstab(g.priced,g.hw))[1])
# per-season market calibration slope
import statsmodels.api as sm
print("\nPer-season recalibration (slope should be 1, intercept 0):")
for S,gr in d.groupby("season"):
    p=gr.p_mkt.values; yv=gr.home_won.values
    X=sm.add_constant(np.log(p/(1-p)))
    r=sm.Logit(yv,X).fit(disp=0)
    print("  %d n=%3d intercept=%+.3f(t%+.2f) slope=%.3f(t_vs1 %+.2f) Brier=%.4f"%(
      S,len(gr),r.params[0],r.params[0]/r.bse[0],r.params[1],(r.params[1]-1)/r.bse[1],np.mean((p-yv)**2)))
