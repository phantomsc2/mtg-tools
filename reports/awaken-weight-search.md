# Awaken importance sensitivity

Same 59,109-base bounded pool: 26 lands, 1–2 Swamps, 0–1 Island, 0–1 Forest,
four-copy nonbasics. No Passage. Same conditional direct metric and equal play/draw weighting.

Multiply each Awaken copy's importance by w; other cards retain weight one. Renormalize
by total weighted copies, 31+3w. Modes stay uniform within a card. Minimize
1 - weighted_success + 2/625 * (shocks + Towns).

First change above w=1: **w=1.098974706600** (tie at the exact boundary).
Selected weight: **1.1**, an increase of 10.0000%.
First successor remains optimal until 1.129317364292.

| Land | Before | After |
|---|---:|---:|
| Swamp | 2 | 2 |
| Overgrown Tomb | 4 | 4 |
| Watery Grave | 4 | 4 |
| Breeding Pool | 2 | 2 |
| Gloomlake Verge | 2 | 2 |
| Willowrush Verge | 4 | 3 |
| Starting Town | 4 | 4 |
| Cavern of Souls | 4 | 4 |
| Island | 0 | 1 |

| Metric | Before | After |
|---|---:|---:|
| Awaken on play | 75.915641% | 76.234424% |
| Awaken on draw | 80.415822% | 80.701943% |
| Awaken average | 78.165731% | 78.468184% |
| Ordinary color success | 89.696402% | 89.693761% |
| Weighted color success at selected w | 89.595551% | 89.595578% |
| Regularized loss at selected w | 14.884449% | 14.884422% |

All probability, crossing and ranking calculations use exact integer/rational arithmetic.
JSON retains exact fractions. The denominator 31+3w is common across all bases, so
the first optimum change is an exact crossing of linear functions after clearing it.
This is exhaustive within the bounded pool, not unrestricted-basic optimization.
