# Draw-based mana opportunities

## Objective

Each physical spell copy scores independently whenever its selected casting mode
is payable. Alternative copies and costs may select different lands; mana and
spells are not consumed. This measures casting opportunities, not throughput,
win rate, or a probability. Zero-weight spells still occupy physical deck slots.

For a cost with c copies, deck size D, N nonlands and s cards seen, expected
payable copies equal c times the sum over payable land-count vectors of
`product(comb(source_count, drawn_count)) * comb(N-1, s-land_count-1) / comb(D,s)`.
Marking one target copy includes land shortage in the denominator without
enumerating complete spell hands. Casting-mode shares normalize within each
physical spell profile. Spell importance and mode shares remain distinct.

## Payment and availability

Payment uses Hall constraints over subsets of required colors plus total mana.
An integer DP caps supplies at the payment requirements and merges equivalent
states. Each realized source outcome must supply both mana and colors; an
unavailable source supplies neither. The explicit ManaModel defines production,
source limits, and availability. The supplied heuristic assumes one source per
turn, independent source failures, unrestricted rainbow Cavern mana, and no
land-drop or spell sequencing. Shock life payments are assumed possible; life
totals are not simulated.

Typed shocks carry two basic land types. Verge secondary production depends on
qualifying types among lands seen, including unavailable sources. This optimistic
lookahead is an approximation, not a battlefield simulation. Fast, slow, Town,
tapped and tri-land availability schedules remain part of mana evaluation.

## Timing and scores

Uniform scoring averages turns one through seven and play/draw by default.
Half-life weighting uses `w_n = 2**(-(n-1)/h)`, normalized over the retained horizon.
The horizon is the smallest H with `2**(-H/h) < tail_tolerance`; the default
omitted-mass tolerance is 0.05. Raw exponential weights are quantized to 1e-9,
then normalized as fractions. Per-turn opportunity rows remain unweighted.

All results expose one score: normalized weighted casting opportunities. Scores
are comparable across spaces when physical spell profiles, importance, timing,
and production assumptions match. Different half-lives define different objectives.

## Search spaces

ManaSpace holds per-source bounds, total land count, and aggregate family_bounds.
For example, shock (8,12), Town (4,4), basic (0,2) expresses admissible compositions
without changing how a base is scored. The from_colors families argument still
sets bounds per generated source. Fixed sources occupy slots within land_count.

Family totals are disjoint groups. Candidate counting convolves per-group bounded
composition counts after restricting each group total. Enumeration allocates
feasible group totals with suffix-capacity pruning. Validation rejects source,
aggregate and joint-total conflicts. Batch candidate rows and local neighborhoods
use the same constraints. Aggregate limits do not necessarily shrink the tensor
capacity grid, which still depends on per-source upper bounds.

## Evaluation and search

The scalar evaluator retains cost/turn/position rows. Batch construction combines
exact binomial transforms and integer limbs; NumPy is optional for the core.
Component tables hold exact mean opportunities per cost, independent of cost
importance. Weighted rankings use exact integer dot products. Casting-cost
sensitivity compares affine score lines and retains exact closed intervals and
successor swaps. Deterministic tie-breaking uses canonical counts.

Local search first descends via one-land replacements. At a one-land optimum it
checks all valid replacements of up to two lands. An improving paired move
resumes one-land descent, followed by another completion check. Only final
compositions must satisfy aggregate limits, permitting coupled family-preserving
moves whose individual transfers are illegal. Both phases share visit budgets
and cached components. A budget stop does not certify local optimality; a complete
two-land check still does not certify global optimality.

## Compatibility and validation

Local cache identities include the raw-score schema, timing, production model,
source pool, spell profiles, draw configuration and aggregate space bounds.
Legacy result/table schemas require rebuilding. Tests compare physical draw and
source-outcome enumeration, scalar/batch parity, exact casting-weight crossings,
constrained candidate counts, and complete tiny-space neighborhoods.

## Independent historical performance measurements

The following documents preserve measurements of their stated historical
workloads; they are not current optimization recommendations:

- [Availability benchmark](../../reports/joint_availability_profile.md)
- [Reliability feature cost](../../reports/land_reliability_cost.md)
- [Notebook build profile](../../reports/notebook_reliability_profile.md)

Retired result-dependent conclusions and obsolete experiments are recorded in
[ANALYSIS_MIGRATION.md](../../ANALYSIS_MIGRATION.md).
