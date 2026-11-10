# h=2 fixed-shock landscape

Envelope among best-found 8..12-shock representatives; not a global optimum certificate.

| Shocks | Raw opportunities | Marginal gain | Above 8-12 chord | Winning shock penalties |
| ---: | ---: | ---: | ---: | --- |
| 8 | 2.432178342600 | - | +0.000000000000 | 0.003059363366 to infinity |
| 9 | 2.434528038988 | 0.002349696389 | -0.000709666978 | Never |
| 10 | 2.436753141380 | 0.002225102391 | -0.001543927953 | Never |
| 11 | 2.440236555965 | 0.003483414585 | -0.001119876734 | Never |
| 12 | 2.444415796065 | 0.004179240100 | +0.000000000000 | 0.000000000000 to 0.003059363366 |

## Land counts

| Land | 8 | 9 | 10 | 11 | 12 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Breeding Pool | 0 | 1 | 2 | 3 | 4 |
| Cavern of Souls | 4 | 4 | 4 | 4 | 4 |
| Deathcap Glade | 1 | 1 | 1 | 1 | 0 |
| Dreamroot Cascade | 3 | 2 | 1 | 0 | 0 |
| Gloomlake Verge | 0 | 0 | 0 | 2 | 3 |
| Overgrown Tomb | 4 | 4 | 4 | 4 | 4 |
| Shipwreck Marsh | 4 | 4 | 4 | 3 | 2 |
| Starting Town | 4 | 4 | 4 | 4 | 4 |
| Wastewood Verge | 0 | 0 | 0 | 0 | 1 |
| Watery Grave | 4 | 4 | 4 | 4 | 4 |
| Willowrush Verge | 2 | 2 | 2 | 1 | 0 |

## Method

Three diverse cached starts per count; exact shock count enforced in candidate generation.
Each run uses one-land descent followed by complete two-land descent, including coupled moves.
All bounds and the two-basic cap are enforced. Four Caverns and four Towns remain fixed.
Full original casting profiles; half-life 2, horizon 9; penalties are compared after optimizing raw opportunities.
The fixed Town deduction is 0.06 for every base, so it does not affect crossings.

## Decklists

- [8 shocks](moonshadow_h2_fixed_8shocks.txt)
- [9 shocks](moonshadow_h2_fixed_9shocks.txt)
- [10 shocks](moonshadow_h2_fixed_10shocks.txt)
- [11 shocks](moonshadow_h2_fixed_11shocks.txt)
- [12 shocks](moonshadow_h2_fixed_12shocks.txt)

## Penalty interpretation

The endpoint crossing is 0.003059363366. Among these representatives, twelve shocks wins below it and eight wins above it; both tie at the crossing.
Nine, ten and eleven shocks lie strictly below the 8-to-12 chord and never win at a nonnegative linear shock penalty.
This reproduces a direct jump among best-found bases. Complete two-land local optimality and multi-start convergence do not certify a global optimum.
