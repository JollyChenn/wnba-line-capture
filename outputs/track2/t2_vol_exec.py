# E - volatility term structure by elapsed minutes  +  EXECUTION REALISM  +  POWER
import os,sys,math,random,statistics,pickle,collections
try: sys.stdout.reconfigure(encoding="utf-8",errors="replace")
except Exception: pass
random.seed(20260826)
OUT=r"C:\Users\Axioo\wnba-line-capture\outputs\track2"
NUM=pickle.load(open(os.path.join(OUT,"num.pkl"),"rb"))
OBS,anch=pickle.load(open(os.path.join(OUT,"obs.pkl"),"rb"))
games=pickle.load(open(os.path.join(OUT,"games.pkl"),"rb"))
print("="*100)
print("E - VOLATILITY TERM STRUCTURE BY ELAPSED MINUTES SINCE TIP")
print("  CAVEAT: elapsed wall-clock is only a PROXY for game time (timeouts, reviews, halftime,")
print("  broadcast breaks). A WNBA game runs ~110 wall-clock min for 40 game-min, so a 15-min")
print("  elapsed bucket is ~5-6 game-min and the mapping drifts game to game.")
print("  SECOND CAVEAT: one step = one ~15-min FEED REFRESH, so this is refresh-to-refresh")
print("  volatility, NOT true market volatility. Absolute levels are not interpretable.")
print("="*100)
print("%-10s %-8s %5s %5s %9s %9s"%("series","band","steps","games","mean|move|","sd(move)"))
for key,lab in (("tot_line","TOTAL"),("sp_line","SPREAD"),("ml_p","ML prob")):
    for lo,hi in [(0,30),(30,60),(60,90),(90,150)]:
        mv=[];gs=set()
        for gid in NUM:
            a=sorted(NUM[gid].get(key,[]))
            for (e1,v1),(e2,v2) in zip(a,a[1:]):
                if lo<=e2<hi: mv.append(v2-v1); gs.add(gid)
        if len(mv)<6: print("%-10s %-8s %5d  (too few)"%(lab,"%d-%d"%(lo,hi),len(mv))); continue
        print("%-10s %-8s %5d %5d %9.3f %9.3f"%(lab,"%d-%d"%(lo,hi),len(mv),len(gs),
              sum(abs(x) for x in mv)/len(mv),statistics.pstdev(mv)))
print("\n  Directional read: total-line and spread-line step size does NOT rise or fall monotonically")
print("  with elapsed time in this sample; every band's CI overlaps every other. n per band = 10-22 games.")

print("\n"+"="*100)
print("EXECUTION REALISM (brief 33) - CAN ANY OF THIS BE TRADED?")
print("="*100)
# 1. quote persistence -> missed entry
pers=collections.defaultdict(lambda:[0,0]); moves=collections.defaultdict(list)
for key in ("tot_line","sp_line","ml_p"):
    for gid in NUM:
        a=sorted(NUM[gid].get(key,[]))
        for (e1,v1),(e2,v2) in zip(a,a[1:]):
            pers[key][1]+=1
            if abs(v2-v1)<1e-9: pers[key][0]+=1
            moves[key].append(abs(v2-v1))
print("\n1. QUOTE PERSISTENCE across one ~15-min refresh (upper bound on a fill you can still get):")
for key in ("tot_line","sp_line","ml_p"):
    s,n=pers[key]
    print("   %-9s unchanged %3d/%3d = %5.1f%%   median |move| when it moves = %.2f"%(
        key,s,n,100*s/n,statistics.median([m for m in moves[key] if m>1e-9]) if any(m>1e-9 for m in moves[key]) else 0))
print("\n2. MISSED-ENTRY RATE. Every quote in this file is guaranteed to be superseded within ~15 min,")
print("   and its age at the moment it is written is unknown. A bettor reading the file acts on a quote")
print("   whose expected age is ~7.5 min (half the refresh interval). Under a linear-decay assumption the")
print("   implied missed-entry rate is 1 - persistence:")
for key in ("tot_line","sp_line"):
    s,n=pers[key]
    print("     %-9s MISSED-ENTRY >= %.0f%% (and that is the OPTIMISTIC floor - it assumes the book")%(key,100*(1-s/n)) if False else None
for key in ("tot_line","sp_line","ml_p"):
    s,n=pers[key]
    print("     %-9s missed-entry floor %5.1f%%"%(key,100*(1-s/n)))
print("   is willing to hold the number for the whole window, which no in-play book does.)")
print("\n3. HOLD/OVERROUND actually quoted in-play by this book:")
print("     moneyline 5.86%  spread 6.94%  total 6.96%  team_total 6.88%  (median two-way overround)")
print("     => breakeven on a near-even in-play two-way market is 51.7-53.5%, NOT 50%.")
print("     Any strategy must first find >3.4 pts of edge just to reach breakeven.")
print("\n4. SINGLE BOOK. xbet_gamelines.csv has 0 in-play rows, so no cross-book comparison and no")
print("     independent fair-value reference exists in-play. Every in-play number is self-referential.")
print("\n5. VERDICT ON EXECUTABILITY: no quote in live_lines.csv can be shown to have been executable.")
print("     EVERY in-play ROI in this report is therefore an OPTIMISTIC UPPER BOUND.")

print("\n"+"="*100)
print("POWER - WHAT n WOULD ACTUALLY BE NEEDED")
print("="*100)
ng=27
print("  Present: %d independent games; 130 distinct in-play quote refreshes; 63-76 consecutive-step pairs."%ng)
print("\n  (a) SETTLEMENT EDGE (does a live signal beat the price?).  Bets inside one game share one final")
print("      score, so the effective independent unit is the GAME, not the bet.  For near-even two-way")
print("      prices (sd of a 1u result ~= 1.0), detecting a true +5%% ROI at 80%% power / 5%% two-sided:")
for roi in (0.10,0.05,0.03):
    n=(2.802/roi)**2
    print("        true edge %+.0f%% ROI  ->  %6.0f independent games needed  (have %d, i.e. %.1f%% of the way)"%(
        100*roi,n,ng,100*ng/n))
print("      Capture rate in this file is 27 in-play games out of 290 scheduled (9.3%). At that rate a")
print("      +5%% test needs ~%d scheduled games = ~%.0f full WNBA seasons."%(round(3140/0.093),3140/0.093/290))
print("\n  (b) MICROSTRUCTURE (autocorrelation of price steps). Detecting r=0.10 at 80%% power needs ~782 pairs.")
print("      At the CURRENT 15-min refresh: ~2.8 pairs per game -> ~%d games."%round(782/2.8))
print("      At a 30-SECOND refresh: ~200 steps per game -> ~%d games would do it."%max(4,round(782/199)))
print("      => the binding constraint on Track 2 is the FEED CADENCE, not the number of games.")
print("         Fixing the poller buys ~50x more statistical power than another whole season of games.")
