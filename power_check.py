# power_check.py - stop asking "is there a pattern" and ask "could we SEE one if there were".
# ---------------------------------------------------------------------------------------------
# Twelve directions have now come back empty. Before concluding anything about the world, the
# honest question is whether this dataset could detect a real effect at all. The time-dimension
# sweep is the clearest case: 99 starred bets, sliced into cells of 22-77, and the permutation
# ceiling came out at p95 = +42.5% ROI. Any true edge smaller than that is invisible here no
# matter how well it is theorised.
#
# This computes, for the sizes we actually have, what a filter would need to deliver before we
# could tell it apart from luck - and how many bets it would take to see something realistic.
import math, random
random.seed(20260901)

AVG_ODDS = 1.85
BE = 1.0 / AVG_ODDS                      # break-even hit rate, ~54.1%
BASE = 0.62                              # Model S's own hit rate

def roi_of(p, odds=AVG_ODDS): return p*odds - 1

def sim_best_of(ncells, cell_n, p_true, T=4000):
    """the best ROI among `ncells` cells of `cell_n` bets each, when every cell is pure noise
       at p_true - i.e. the bar a real finding has to clear."""
    out = []
    for _ in range(T):
        best = -9
        for _ in range(ncells):
            w = sum(1 for _ in range(cell_n) if random.random() < p_true)
            best = max(best, (w*(AVG_ODDS-1) - (cell_n-w))/cell_n)
        out.append(best)
    out.sort()
    return out[int(T*0.95)], out[T//2]

print("=" * 100)
print("  WHAT A FILTER MUST DELIVER TO BE VISIBLE, at the sample sizes we actually have")
print("=" * 100)
print(f"  assumptions: avg odds {AVG_ODDS}, break-even {100*BE:.1f}%, Model S base rate {100*BASE:.0f}%")
print("")
print(f"  {'cells':>6}{'bets/cell':>11}{'noise p95 ROI':>16}{'hit rate that implies':>24}")
for ncells, cell_n in ((9, 50), (9, 99), (12, 25), (12, 50), (5, 100), (5, 200), (3, 300)):
    p95, med = sim_best_of(ncells, cell_n, BASE)
    implied = (p95 + 1) / AVG_ODDS
    print(f"  {ncells:>6}{cell_n:>11}{100*p95:>15.1f}%{100*implied:>23.1f}%")
print("")
print("  Read the last column as: with this many cells and this many bets each, a filter has to")
print("  hit AT LEAST that rate before it can be told apart from a lucky slice of an already-good")
print("  model. Model S itself hits 62%.")
print("")
print("=" * 100)
print("  HOW MUCH DATA WOULD IT TAKE TO SEE A REAL, MODEST FILTER?")
print("=" * 100)
print("  Suppose a filter genuinely lifts the hit rate from 62% to 68% - a big, useful effect.")
print("  How many bets in that cell before it clears the noise ceiling of a 9-cell search?")
print("")
print(f"  {'bets in cell':>13}{'noise p95':>12}{'true ROI at 68%':>18}{'detectable?':>14}")
true_roi = roi_of(0.68)
for n in (25, 50, 100, 200, 300, 500):
    p95, _ = sim_best_of(9, n, BASE)
    print(f"  {n:>13}{100*p95:>11.1f}%{100*true_roi:>17.1f}%{('YES' if true_roi > p95 else 'no'):>14}")
print("")
print("=" * 100)
print("  WHAT THAT MEANS IN NIGHTS")
print("=" * 100)
for n in (100, 200, 300):
    print(f"    {n} bets in a single cell  ->  {n/2.0:.0f} betting nights at 2/night for the cell alone;")
    print(f"       if the cell is half the model that is {n*2/2.0:.0f} nights of Model S, about "
          f"{n*2/2.0/7:.0f} weeks")
print("")
print("  CONCLUSION. The searches were not badly designed and the ideas were not bad - the")
print("  dataset simply cannot resolve anything below roughly a 40% ROI cell at current sizes,")
print("  and no honest filter is that strong. The binding constraint is bets, not hypotheses.")
