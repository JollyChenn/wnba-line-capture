import pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
import statsmodels.api as sm
from scipy import stats
p=pd.read_csv("outputs/gm/gm_preds.csv").merge(pd.read_csv("outputs/gm/gm_own_feats.csv"),on="game_id",how="left",suffixes=("","_x"))
d=pd.read_csv("outputs/gm/gm_ml_base.csv")
p=p.merge(d[["game_id","home_margin","spread","pnews","pstr","telo"]],on="game_id",how="left",suffixes=("","_d"))
pm=p.p_mkt.values; y=p.y.values; ml=np.log(pm/(1-pm)); elo=p.o_elo.values
pe=1/(1+10**(-(elo+80)/400)); dis=pe-pm
Z={"o_elo/100":elo/100,"o_rest":p.o_rest.values,"o_b2bh":p.o_b2bh.values,"o_b2ba":p.o_b2ba.values,
   "o_form5":p.o_form5.values,"o_form10":p.o_form10.values,"elo_dis":dis,
   "pnews":p.pnews.values,"pstr":p.pstr.values,"telo/100":p.telo.values/100}
print("=== MECHANISM: logit P(home win) = a + b*market_logit + c*z  (c=0 if close efficient) ===")
for k,v in Z.items():
    ok=~pd.isna(v)&~np.isnan(ml)
    X=sm.add_constant(np.column_stack([ml[ok],np.asarray(v,float)[ok]]))
    r=sm.Logit(y[ok],X).fit(disp=0)
    print(f"  z={k:10} c={r.params[2]:+.4f} se={r.bse[2]:.4f} t={r.params[2]/r.bse[2]:+.2f} p={r.pvalues[2]:.3f} n={ok.sum()}")
ok=~np.isnan(elo)
cols=["o_elo/100","o_rest","o_b2bh","o_b2ba","o_form10"]
X=sm.add_constant(np.column_stack([ml[ok]]+[np.asarray(Z[k],float)[ok] for k in cols]))
r1=sm.Logit(y[ok],X).fit(disp=0); r0=sm.Logit(y[ok],sm.add_constant(ml[ok])).fit(disp=0)
lr=2*(r1.llf-r0.llf); print("  JOINT LR (5 own feats) chi2=%.2f df=5 p=%.3f n=%d"%(lr,1-stats.chi2.cdf(lr,5),ok.sum()))
resid=p.home_margin.values+p.spread.values
print("\n=== RAW OUTCOME MECHANISM: ATS residual (home_margin - market home margin) ===")
for k,v in Z.items():
    v=np.asarray(v,float); ok=~np.isnan(resid)&~np.isnan(v)
    c=np.corrcoef(v[ok],resid[ok])[0,1]; n=ok.sum(); t=c*np.sqrt(n-2)/np.sqrt(1-c*c)
    print(f"  {k:10} r={c:+.4f} t={t:+.2f} n={n}  mean_resid_if_z>med={resid[ok][v[ok]>np.median(v[ok])].mean():+.2f} vs {resid[ok][v[ok]<=np.median(v[ok])].mean():+.2f}")
# b2b situational raw check
for lbl,m in [("home on b2b",p.o_b2bh.values==1),("away on b2b",p.o_b2ba.values==1),("neither",(p.o_b2bh.values==0)&(p.o_b2ba.values==0))]:
    m=m&~np.isnan(resid)
    print(f"  {lbl:12} n={m.sum():5} mean ATS resid={resid[m].mean():+.2f} (se {resid[m].std()/np.sqrt(m.sum()):.2f})  home win rate {y[m].mean():.3f} vs mkt {pm[m].mean():.3f}")
