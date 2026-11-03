# Robustness of the land-model conclusion

## What was tested

Same no-Cavern Standard-filtered UBG pool: all 32,211 candidates, 26 lands,
current notebook's 34 nonland cards, turns 1-7, both positions, opening seven.
Every scenario was reoptimized over the complete pool. No hand sampling.
Scoring sweeps reused saved exact components. Structural stress tests built
new exact components in isolated experimental backends; production evaluator
and notebook settings were not changed.

The question is whether V1's selected composition remains close to V2's, and
whether turning reliability off causes a larger composition error. Regret is
(best score minus candidate score) / best score within the evaluation model.
These percentages are opportunity-score losses, not win-rate losses.

## Penalties and spell weights

| Sweep | Cases | V1 winner's loss under V2 | Off winner's loss under V2 |
| --- | ---: | --- | --- |
| Shock/Town penalties | 25 | 0-0.113%; median 0.032% | 0.642-2.881%; median 1.108% |
| Spell/mode weights | 4 | 0-0.176% | 0.977-2.296% |

In all 29 scoring scenarios, ignoring reliability loses more than selecting
V1's optimum. These are chosen stress settings, not independent statistical
samples or calibrated life costs.

Penalty grid is shock {0, .007, .014, .028, .05} crossed with Town
{0, .005, .01, .02, .04}. Each model optimizes under the same setting. There
are five distinct V2 optima across the grid. Blooming Marsh ranges from two
to four; Botanical Sanctum remains zero. The worst V1 loss is 0.112858% at
shock .028 / Town .02, requiring one replacement relative to the V2 optimum.

Spell cases use the original penalties .014/.01:

| Perturbation | V1 loss under V2 | Off loss under V2 | V1-to-V2 replacements |
| --- | ---: | ---: | ---: |
| Double importance of MV <=2 costs | 0% | 0.977% | 0 |
| Double importance of MV >=4 costs | 0.037% | 2.296% | 1 |
| Double relative weight of MV <=2 payment modes | 0.080% | 1.052% | 2 |
| Double relative weight of MV >=4 payment modes | 0.176% | 1.272% | 3 |

Mode experiments renormalize within each physical spell and keep physical
card counts and deck size fixed. Existing components are rescaled by the exact
ratio of new weighted mode-copy shares to original copy shares. Importance
experiments change preferences directly; mode experiments change the payment
profile's internal shares. No alternate turn horizon was tested.

## Single-failure structural alternative

To stress independent land failures, allow at most one drawn source to fail on
a turn. For k lands seen on turn T, a particular unreliable source copy fails
with probability 1/max(k,T). Sum over which source fails, or none, then check
joint payment. Earlier/all-other seen sources remain usable for selection.

For k<=T this preserves the existing marginal failure probability 1/T while
changing correlations. For surplus draws k>T it also reduces the marginal
failure rate to 1/k. Therefore this is not a pure correlation isolation and not
a full sequencing model: it still ignores actual draw arrival and played-land
selection. It is an exact count-based stress test under its stated assumptions.
The kernel was checked against exact latest-land enumeration for all four-land
Town/basic mixes on turn four, including four Towns being unable to pay MV4.

Results under this alternative at the original penalties:

- Its optimum is exactly the original V1 composition.
- Original V2 winner ranks eighth; loss 0.001280416, or **0.042851%**.
- Original off winner ranks 1,523rd; loss 0.027009152, or **0.903898%**.

This supports near-equivalence in composition quality between V1 and V2, but
shows that V2's exact two-Blooming recommendation depends on the failure model.

## Conservative Verge endpoint

Disable all Verge secondary production while retaining their primary colors,
land bounds, and independent availability. This is a deliberately pessimistic
endpoint, not an estimate of how frequently a Verge actually enables. Current
all-seen enabling is the optimistic endpoint. Regret is not guaranteed to vary
monotonically between these endpoints.

Reoptimize V1 and V2 under this same change. Off was not rebuilt for this endpoint.

| Source | V1 endpoint optimum | V2 endpoint optimum |
| --- | ---: | ---: |
| Blooming Marsh | 4 | 4 |
| Botanical Sanctum | 4 | 4 |
| BG shock | 4 | 4 |
| UB shock | 4 | 4 |
| UG shock | 0 | 1 |
| Town | 4 | 4 |
| BG Verge | 0 | 0 |
| UB Verge | 2 | 1 |
| UG Verge | 4 | 4 |

V1's endpoint winner ranks fifth under the endpoint V2 model and loses
0.000698081, or **0.024018%**. They differ by one land. However, the endpoint
V2 optimum differs by eight replacements from the original V2 optimum,
including restoring all four Botanical Sanctum. The exact composition is
therefore much more sensitive to Verge modeling than the original V1/V2 gap.
This extreme alone does not tell us where a realistic played-enabler model lands.

## Interpretation and limits

The narrow conclusion survived every tested scenario: V1 and V2 choose
compositions very close in score, and reliability-off performs materially worse
where it was compared. The exact land mix did not survive all changes. In
particular, omitting Botanical Sanctum and choosing exactly two Blooming Marsh
should not be treated as robust deckbuilding facts.

V2 remains internally joint, but its extra precision does not establish that it
is a better predictor of actual games. The remaining priorities for model
validation are actual draw/land-drop timing, selection among surplus lands,
played-only Verge enabling, and spell competition/one-time casting. These were
not solved by the stress tests. No confidence intervals or real-game validation
are implied by these deterministic scenario results.

[Raw results](robustness_results.json) retain every optimum and cross-evaluation.
[Experiment script](robustness_experiment.py) uses the retained local component
pickles and V1 backend snapshot in .cache. It can reproduce the sweeps and
structural builds without modifying production code.
