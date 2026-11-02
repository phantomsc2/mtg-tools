# Basics under the direct metric

Added Island and Forest metadata and optional category names to the exact
binomial-grid evaluator. Original search category lists remain unchanged.
New tests compare these category substitutions with the scalar exact evaluator,
including land-type activation of Verges. All 24 tests pass.

`mana_basic_search.py` evaluates 59,109 bases with 26 lands, at least one Swamp,
up to two Swamps, one Island and one Forest, and the original four-copy nonbasic
pool. It also evaluates every one-card basic substitution from each original
8–12-shock optimum. Coefficients 0, .003, .004, .005, .008 retain the same
per-card shock/Town penalty. Probabilities, weights and comparisons are exact.

This is explicitly a bounded sensitivity analysis, not a proof of the global
optimum with unrestricted basics. Every best bounded base has two Swamps,
so more basic copies may merit further search. Basics are not subject to a
rules-based four-copy limit; these bounds limit only this experiment.

A second Swamp is favorable at every tested coefficient. Island is favorable
as a one-card swap at .004 and above; Forest becomes favorable at .008. With
zero penalty, replacing Wastewood with Swamp already improves color success
by .043807 percentage points through basic-type activation of other Verges.

At lambda=.004, the best bounded base is 2 Swamp, 1 Island, 4 Tomb, 4 Grave,
1 Pool, 2 Gloomlake, 4 Willowrush, 4 Town and 4 Cavern. Raw success 89.370750%;
13 penalized lands rather than 14. Penalized score improves .182889 percentage
points despite losing .217111 points of raw success. Forest is absent.

At .008 the best bounded base includes 2 Swamp, 1 Island and 1 Forest, with
2 Tomb, 4 Grave, 2 Gloomlake, 2 Wastewood, 4 Willowrush, 4 Town and 4 Cavern.
This has six shocks; the former eight-shock optimum was conditional on the
narrower no-extra-basics pool. Old penalty-to-shock-count mappings need to be
recomputed if basics are admitted.

## Lowering lambda from the three-basic version

The full 59,109-base evaluation now saves exact optimality intervals to
reports/basic-land-penalty-frontier.csv and .md. Starting at lambda=.004,
the 2-Swamp/1-Island, nine-shock base first loses optimality on decreasing
lambda at .0032565236543952206 (rounded). The new winner replaces Island
with a second Breeding Pool: it has two basics and ten shocks. Its raw success
is 89.6964020842%, versus 89.3707497188% before. The exact transition is the
difference in success fractions divided by the one additional penalized land.

Choose lambda=.0032 (0.32 percentage points per shock/Town). It lies strictly
inside the ten-shock interval (.0031093334380109822, .0032565236543952206).
Below the lower endpoint, eleven shocks win instead. The same two Swamps,
four Tombs, four Graves, two Gloomlakes, four Willowrush, four Towns and four
Caverns are retained at the ten-shock transition. No Wastewood or Forest.
Reports/basic-shock-transition.md records the full composition and threshold.
The exact interval calculation includes every count class from the full
neighborhood; it is not a claim about unrestricted numbers of basics.
