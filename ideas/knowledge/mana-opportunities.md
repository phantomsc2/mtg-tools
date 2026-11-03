# Draw-based mana opportunities

`mana_opportunities.py` replaces the Sultai-specific analysis/search/report pipeline.
The core accepts cost counts with optional weights, and a supplied mana base.
`examples/sultai.py` is the sample cost profile; its illustrative lands replace the
original deck's special sources. The raw decklist is retained
only as sample data. Existing generic hand/search utilities remain independent.

Each drawn physical copy scores independently whenever its cost is payable.
Alternatives may use different land selections; neither spells nor mana are
consumed. This deliberately counts backups and ignores sequencing. Scores are
uniform means across T1 through T7 and both play/draw positions by default.
Do not interpret the result as win rate, casting throughput, or a probability.

For a cost with c copies, deck size D, N nonlands and s cards seen, its expected
payable copies are c times the sum over payable land vectors of
`product(comb(source_count, drawn_count)) * comb(N-1, s-land_count-1) / comb(D,s)`.
This marks each target copy in turn. It includes mana shortage in the denominator
and avoids enumerating joint spell hands. Zero-weight cards still affect draws.

Payment uses Hall's condition for all subsets of required colors. An integer DP
tracks land count and capped subset supplies, merging interchangeable sources.
Unconditional one-mana sources mean successful payment needs no battlefield search:
a matching plus enough generic sources fits within the turn's land-drop limit.
Payment weights are cached independently of importance and penalties.

Town and shock penalties are independent coefficients per land in the base,
subtracted after averaging opportunities. Their scale is raw opportunities per
turn; old penalties on normalized conditional coverage are not transferable.

The evaluator uses only the standard library; batch search uses NumPy. Tests compare against physical draws
and exhaustive mana assignments. Full repository tests require the neighboring
leitwerk checkout on PYTHONPATH if it is not installed in the test environment.

## Shared search components

`mana_search.py` averages exact per-turn expectations from the evaluator into a
component vector per base. It stores no draw-dependent importance or penalty;
ranking is a rational dot product minus composition penalties. Duplicate cost
entries use a copy-weighted default importance, so ranking reproduces evaluate.
Overrides replace that cost's importance rather than multiplying it.

ManaSpace uses caller-supplied lower/upper bounds and a fixed total land count.
Its counting DP sizes the exhaustive pool without enumeration. Tables cover the
complete bounded pool. The earlier neighborhood-search mode has been removed.

Sensitivity treats a selected absolute weight or penalty x as a nonnegative
variable. Each base is a line a+b*x. Baseline optimality is the intersection of
linear inequalities against all candidates; equalities count as ties. A finite
endpoint gives the outward successor by extremal slope. Nonoptimal references
have no next-optimum transitions at the current settings.
All thresholds and intervals use Fraction, including decimal parameter inputs.
Claims are always relative to the evaluated candidate set, never to all possible
land pools. Scalar table construction evaluates bases independently; the
batch backend shares a binomial transform across the capacity grid.

The table builder accepts an optional candidate-iterable wrapper for progress
reporting. The notebook wraps it with tqdm, while the core has no UI dependency.
`candidate_count()` supplies the row progress total.

## Alternate modes

Spell profiles hold physical count, importance, and CastingMode entries whose
weights normalize per profile. SpellCost is the unchanged single-mode shorthand.
spell_components computes physical nonlands separately from rational mode-copy
shares, preventing alternatives from enlarging the deck. The evaluator and
search builder share this decomposition. Table columns retain unweighted mode
shares; default importance is the share-weighted mean for each cost. Cost-weight
crossings stay affine with mode shares fixed. Changing normalized mode shares
requires rebuilding the table. The Sultai fixture now includes incarnation
payment alternatives, with no copied-card or board-discount scenarios.

## Verge payment backend

ManaSource supports explicit basic land types. Basics infer their type, shocks
default to untyped and can explicitly carry both types, Town, Cavern, and Verges
carry none. VERGE_RULES registers UB (Gloomlake: U first), BG (Wastewood: G first),
and UG (Willowrush: U first), including the secondary color and either/or type
condition. Published card text:
[Gloomlake](https://mtg.wtf/card/dsk/260/Gloomlake-Verge),
[Wastewood](https://mtg.wtf/card/dft/268/Wastewood-Verge),
[Willowrush](https://mtg.wtf/card/dft/270/Willowrush-Verge).

The former exact battlefield/draw enumeration backend has been removed.
Verge activation now uses basic land types anywhere among the lands seen, even
if the enabling land would exceed the turn's land-drop limit. This is deliberate
optimism; payment still requires enough distinct sources and cost <= turn.

The capped-supply DP partitions draws by their final relevant type mask. For
each mask, Verge production is fixed; states track land count, observed type
mask, and capped Hall supplies. Sources carrying types outside the target mask
must be absent. Only states whose observed mask equals the target contribute,
so every draw is counted exactly once. Groups merge sources with identical
supply/type signatures. Only types enabling a secondary color required by the
current cost are tracked; irrelevant conditions fall back to the original DP.
Results are cached independently of importance, penalties, and turn limits.

Source typing, Verge lookup rules, zero Verge composition penalty, and table
scoring/crossings are unchanged. Small physical-draw tests use all-seen types
and enumerate mana assignments independently to check the approximation.

## Reference pool and accelerated table creation

The notebook and Sultai script use one fixed Swamp, no Islands/Forests, and up
to four of each typed Sultai shock, Verge, Starting Town, and Cavern. There are
3,144 legal bases; the capacity grid has 781,250 cells. The starting base has
1 Swamp, 12 shocks, 4 Town, 4 Cavern, and Verges 3 Gloomlake / 1 Wastewood /
1 Willowrush. Spell modes and the T1?T7 opportunity metric remain unchanged.
Both Town and Cavern produce unrestricted rainbow mana and have no basic land
types. Cavern's creature restrictions remain outside this model. Only Town
incurs town_penalty; shock_penalty applies only to shocks. Both coefficients
start at 0.01 in the notebook and can be varied independently. Public APIs and
component fields now use shock/town names instead of dual/rainbow names.

mana_batch builds Hall feasibility on sparse count grids, with enabling types
from all lands seen. It averages nonland-draw factors over eligible turns and
positions, then applies the multidimensional binomial transform. Rational
numerator coefficients split into integer limbs. A sum-of-binomial land-subset
bound selects limb width so every partial transform fits int64; reconstruction
and final Fraction arithmetic use Python integers. This avoids both floating
rounding and one transform per turn/position. Each cost emits a full column.

Auto selects batch for exhaustive pools without candidate-count or grid-size cutoffs. Explicit scalar remains the exhaustive correctness oracle;
explicit batch permits comparing the same candidate subset. Auto falls back on
missing NumPy or an unsafe integer bound. The candidate progress wrapper now
reports row assembly in batch mode; component_progress reports cost transforms.
Notebook UI owns both tqdm wrappers. No large-pool notebook run is needed for
validation; the reduced reference pool is benchmarked separately against scalar.

Before splitting Town/Cavern, measured merged-pool table build: batch 0.786s versus scalar 36.135s (45.9x).
The complete ComponentTable objects compared equal, including every exact
component fraction across all 1,548 bases. A separate example run took 0.796s
for construction and 0.151s for ranking plus a crossing query. These are local
measurements of the current seven-turn metric, not the historical conditional
coverage objective. That timing used the earlier, now removed neighborhood analysis.

After splitting Town/Cavern and renaming shocks: the 3,144-base batch table
built in 2.448s, ranking plus crossings in 0.304s before report optimization. Exact batch/scalar agreement and separate Town/Cavern
penalties are covered by the 51-test suite.

The notebook now allows 0–2 of all five basic types, retaining its one-Swamp
starting composition and four-copy nonbasic bounds. Its pool has 4,581,982 bases
and 94,921,875 capacity-grid cells. The notebook prints grid size before
building; the full bounded pool is scanned. The command-line reference example remains the smaller
fixed-Swamp pool for reproducible performance comparisons. Only notebook inputs,
bounds, and candidate count were validated; no analysis was executed.

## No resource cutoffs

Removed the one-million-cell backend guard and automatic dispatch cutoff, plus
the 64-candidate batching threshold. Exhaustive auto builds now attempt batch
regardless of pool/grid size. Memory allocation errors propagate; there is no
memory-based scalar fallback. Integer overflow checks/fallback remain for exact
arithmetic, and missing NumPy can still select scalar. Notebook size reporting
is informational only, and the previous cutoff warning has been removed.

## Efficient exhaustive reports

Removed the search mode argument, neighborhood generators, mode fields, and
pairwise comparison records. Full scan is the only search scope. ComponentTable
lazily caches integer columns at one exact denominator per cost. score() returns
a reusable ScoredTable with integer raw/penalized scores at a common denominator.
rank(limit=5) uses heap selection and creates swaps only for the selected rows;
rank() without a limit still returns all candidates. Crossings reuse that score
snapshot, group parallel lines by exact slope, and retain each group's highest
line. Identical parallel lines use replacement distance and canonical counts to
preserve successor tie rules. Integer cross multiplication finds interval bounds;
only final endpoints/results become reduced Fractions. This preserves every
candidate's effect on the envelope without per-candidate Fraction arithmetic or
unused OUT/IN objects. The notebook scores once and uses the snapshot throughout.

Validation compares full/top-k rankings and cost/penalty crossings against an
independent Fraction oracle, including zero weights, ties, boundary transitions,
and nonoptimal references. Existing scalar/batch component checks still apply.

Report-only benchmark: 263,274 real candidate-count vectors with 18 realistic
component columns sampled cyclically from the reference table (no expanded-pool
draw analysis) took 2.015s for a cold report, 0.542s with cached integer columns.
On the same 50,000-row workload, the previous implementation took 7.986s versus
0.344s (23.2x); top results and exact crossing endpoints/successors matched.
The actual 3,144-base reference report took 0.022s. All 52 tests pass. These are
local measurements, not guarantees of notebook timing on other component data.

## Notebook result layout

Results are ordered: optimum metrics/composition, top ten candidates, cost-weight
sensitivities for all canonical costs, then shock/Town penalty sensitivities.
Candidate changes are relative to the starting base; sensitivity changes are
relative to the optimum. OUT and IN are separate columns. Boundaries show
absolute parameter values, with exact results retained in analysis dictionaries.
All sections reuse the score snapshot. Report helpers and layout were exercised
on the small 3,144-base reference table without running the notebook's expanded
pool; all 18 cost sensitivities and both penalty sensitivities were present.
