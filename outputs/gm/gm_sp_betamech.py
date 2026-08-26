# MECHANISM CHECK on the one surviving statistical signal: beta(ats ~ edge) > 0.
# If real information -> beta should be stable across book-count, and robust to trimming.
# If a consensus-line-quality artifact -> beta should be bigger where fewer books were quoted.
import numpy as np, pandas as pd, os, pickle
D=r"C:\Users\Axioo\wnba-line-capture"
A=pd.read_csv(os.path.join(D,"outputs","gm","gm_model_rows.csv"))
P=pickle.load(open(os.path.join(D,"outputs","gm","gm_preds.pkl"),"rb"))
A["pred"]=P["('ridge a=300', 'margin', False)"]
B=pd.read_csv(os.path.join(D,"outputs","gm","gm_modelB_rows.csv")); B["pred"]=B.predB
def prep(df):
    g=df[df.pred.notna()&(df.ats!=0)].copy(); g["edge"]=g.pred-g.mkt; return g
def bt(g,lbl):
    x=g.edge.values;y=g.ats.values
    X=np.column_stack([np.ones(len(x)),x]);b=np.linalg.lstsq(X,y,rcond=None)[0]
    r=y-X@b; se=np.sqrt((r@r/(len(x)-2))*np.linalg.inv(X.T@X)[1,1])
    print(f"    {lbl:34} n={len(g):5d} beta={b[1]:+.4f} se={se:.4f} t={b[1]/se:+5.2f}")
    return b[1]
for nm,g in (("A_feats",prep(A)),("B_elo",prep(B))):
    print(f"\n{nm}:")
    bt(g,"ALL")
    med=g.n_bk_sp.median()
    bt(g[g.n_bk_sp<=med],f"few books (n_bk_sp<={med:.0f})")
    bt(g[g.n_bk_sp>med], f"many books (n_bk_sp>{med:.0f})")
    # trim extremes
    for q in (0.99,0.95,0.90):
        c=g.edge.abs().quantile(q); bt(g[g.edge.abs()<=c],f"trim |edge| top {(1-q)*100:.0f}%")
    # per side
    bt(g[g.edge>0],"edge>0 (home-lean) only")
    bt(g[g.edge<0],"edge<0 (away-lean) only")
    # is it just a home-field level effect? add spread as control
    x=np.column_stack([np.ones(len(g)),g.edge.values,g.mkt.values,g.spread.abs().values])
    b=np.linalg.lstsq(x,g.ats.values,rcond=None)[0]
    r=g.ats.values-x@b; V=(r@r/(len(g)-4))*np.linalg.inv(x.T@x)
    print(f"    {'w/ controls (mkt, |spread|)':34} n={len(g):5d} beta={b[1]:+.4f} se={np.sqrt(V[1,1]):.4f} t={b[1]/np.sqrt(V[1,1]):+5.2f}")
    # rolling: first half vs second half of the test window chronologically
    g2=g.sort_values(["season","date"]); h=len(g2)//2
    bt(g2.iloc[:h],"chronological first half"); bt(g2.iloc[h:],"chronological second half")
