# Regularized actual-pool search

Uses all 3,144 exact actual-pool results: 26 lands, fixed Swamp, four-copy limits, Sultai shocks/Verges,
Starting Town and Cavern. No Sewers. The same spell package and mode weights remain in place.

Minimize L_regularized = 1 - success + lambda * (shock count + Starting Town count).
Selected lambda = 1/250 = 0.40% score penalty per included shock or Town.
This is an additive deck-composition penalty, not an estimate of expected life paid.

## Winning base

- 1 Swamp
- 4 Overgrown Tomb
- 4 Watery Grave
- 2 Breeding Pool
- 3 Gloomlake Verge
- 1 Wastewood Verge
- 3 Willowrush Verge
- 4 Starting Town
- 4 Cavern of Souls

Unregularized success: 89.587861%.
Unregularized loss: 10.412139%.
Regularized loss: 16.012139%.

## Exact optimality intervals

Bounds below are percentage-point penalty per shock or Town. Endpoints can tie.

| Shocks | Towns | Raw success | Penalty from | Penalty to |
|---:|---:|---:|---:|---:|
| 12 | 4 | 90.196576% | 0.000000 | 0.259778 |
| 11 | 4 | 89.936798% | 0.259778 | 0.348937 |
| 10 | 4 | 89.587861% | 0.348937 | 0.458013 |
| 9 | 4 | 89.129848% | 0.458013 | 0.661135 |
| 8 | 4 | 88.468713% | 0.661135 | 0.914933 |
| 7 | 4 | 87.553780% | 0.914933 | 1.140779 |
| 6 | 4 | 86.413001% | 1.140779 | 1.439504 |
| 5 | 4 | 84.973498% | 1.439504 | unbounded |

## Top five at selected penalty

| Rank | Shocks | Raw success | Regularized loss | Composition |
|---:|---:|---:|---:|---|
| 1 | 10 | 89.587861% | 16.012139% | 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 2 Breeding Pool, 3 Gloomlake Verge, 1 Wastewood Verge, 3 Willowrush Verge, 4 Starting Town, 4 Cavern of Souls |
| 2 | 10 | 89.574195% | 16.025805% | 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 2 Breeding Pool, 2 Gloomlake Verge, 1 Wastewood Verge, 4 Willowrush Verge, 4 Starting Town, 4 Cavern of Souls |
| 3 | 11 | 89.936798% | 16.063202% | 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 3 Breeding Pool, 3 Gloomlake Verge, 1 Wastewood Verge, 2 Willowrush Verge, 4 Starting Town, 4 Cavern of Souls |
| 4 | 10 | 89.532810% | 16.067190% | 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 2 Breeding Pool, 3 Gloomlake Verge, 4 Willowrush Verge, 4 Starting Town, 4 Cavern of Souls |
| 5 | 9 | 89.129848% | 16.070152% | 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 1 Breeding Pool, 3 Gloomlake Verge, 1 Wastewood Verge, 4 Willowrush Verge, 4 Starting Town, 4 Cavern of Souls |

All comparisons use exact fractions; displayed values are rounded.
Regenerate the underlying grid with `python mana_search.py`, then run
`python mana_regularization.py --penalty 0.004`.
