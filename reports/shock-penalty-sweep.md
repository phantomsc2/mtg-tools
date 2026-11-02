# Direct-metric optima with 8–12 shocks

Minimize color failure + lambda * (shocklands + Starting Towns), with the same penalty for both.
Rechecked all 3,144 26-land bases: one fixed Swamp, four-copy limits, Sultai shocks/Verges,
Starting Town and Cavern. No Sewers or fifth copies. All original spell modes and weights retained.
Starting Town was allowed to vary; every reported optimum keeps four. All also keep four Caverns.

## Compositions

Every row shares: 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 3 Gloomlake Verge, 4 Starting Town, 4 Cavern of Souls.

| Shocks | Breeding Pool | Wastewood Verge | Willowrush Verge | Color success | Color loss |
|---:|---:|---:|---:|---:|---:|
| 12 | 4 | 1 | 1 | 90.196576% | 9.803424% |
| 11 | 3 | 1 | 2 | 89.936798% | 10.063202% |
| 10 | 2 | 1 | 3 | 89.587861% | 10.412139% |
| 9 | 1 | 1 | 4 | 89.129848% | 10.870152% |
| 8 | 0 | 2 | 4 | 88.468713% | 11.531287% |

## Penalties selecting each composition

Penalty units below are percentage points of normalized score per included shock or Town.
Adjacent optima tie at interval endpoints; interiors uniquely select the reported base.

| Shocks | Penalty from (pp) | Penalty to (pp) | Example penalty (pp) | CLI lambda |
|---:|---:|---:|---:|---:|
| 12 | 0.000000 | 0.259778 | 0.000 | 0 |
| 11 | 0.259778 | 0.348937 | 0.300 | 0.003 |
| 10 | 0.348937 | 0.458013 | 0.400 | 0.004 |
| 9 | 0.458013 | 0.661135 | 0.500 | 0.005 |
| 8 | 0.661135 | 0.914933 | 0.800 | 0.008 |

The first three cuts replace Breeding Pool with Willowrush Verge. The fourth replaces
the last Breeding Pool with Wastewood Verge. Overgrown Tomb and Watery Grave stay at four.
Raw color success drops from 90.196576% at twelve shocks to 88.468713% at eight shocks.
This penalty is a preference over deck composition, not expected life paid in a game.
Starting Town and Cavern remain particularly valuable under the universal-creature Cavern
assumption and uniform weighting of white modes.

Results and interval comparisons use exact fractions. Displayed decimals are rounded.
Regenerate with `python mana_search.py` followed by `python mana_regularization.py`.
