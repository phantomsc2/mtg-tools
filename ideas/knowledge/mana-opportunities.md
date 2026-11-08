# Draw-based mana opportunities

## Notebook turn horizon (2026-11-03)

The build cell exposes `TURNS = 7` and passes it to `build_component_table`.
Components store means across turns, not individual turn values, so the horizon
must be chosen before construction. Changing it requires rebuilding and rerunning
the report; penalties remain editable afterward without rebuilding.

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
and exhaustive mana assignments.

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


## Explicit color and family selection

`mana_lands` owns ManaSource, source eligibility, land-type validation, and all ten
Verge rules. `ManaSpace.from_colors(land_count, colors, families=..., overrides=...)`
expands explicit family bounds into the existing concrete bounded pool. Basics
and duals stay within selected colors; Town and Cavern retain rainbow production.
Generated shocks are typed. Overrides replace selected-source bounds only.
Neither spells nor a reference base determine eligible colors or land count.
Selected colors do not force every candidate to produce all those colors.

Full Verge card-text reference, checked 2026-11-03:
https://managathering.com/lands/by-cycle/verge-lands/
The unconditional colors for WU/WB/WR/WG/UB/UR/UG/BR/BG/RG are respectively
W/B/W/G/U/R/U/B/G/R; the secondary color unlocks with either corresponding
basic land type among all lands seen, preserving the existing approximation.

The notebook uses independent LAND_COUNT, COLORS, and LAND_FAMILIES inputs,
retaining its edited spell/reference inputs. It prints candidate count and the
product of (source upper bound + 1) before building. Both can grow sharply with
more colors and families; construction remains exhaustive without cutoffs.
Scalar/batch equality is checked on small generated pools for every newly
supported Verge pair; the full five-color space is inspected without evaluation.


## Independent land availability (2026-11-03)

Per drawn multiset, multiply the optimistic color-payment indicator by the
probability that at least MV lands independently succeed. A source played on a
uniform turn 1..T is available on T if played earlier or if it enters untapped
on T. Thus Town/fast are 1 through T3 then (T-1)/T; slow is 0, 1/2, then 1;
tapped is (T-1)/T; basic/shock/Verge/Cavern remain 1. Assume one drop each turn
for fast/slow conditions and life paid for shocks. New fast/slow/tapped kinds
are untyped duals with all ten pairs, no extra penalty, and explicit pool opt-in.

The factor is the >=MV tail of product((1-r_i)+r_i*z)^n_i. Surplus drawn lands
compensate; zero costs have factor 1. Sources failing availability still count
for colors and seen Verge-enabling types. This factorization is deliberately
optimistic about color bottlenecks and makes independent failures possible even
when real land order would correlate them. Four Towns for MV4 on T4 score
81/256; one Town plus three basics score 3/4. Permanent Passage choices remain
outside the model.

Scalar counting adds a capped available-count state beside Hall supplies and
seen types, grouping equivalent sources. Integer-scaled binomial outcome masses
avoid Fraction arithmetic within the DP; normalization happens after each final
mask sum. Cache keys include exact source availability rates. Batch still checks
colors on the whole drawn-count grid, groups turns by rate signature, and uses
binomial-tail lookups on total/certain/uncertain drawn counts. Currently all
uncertain classes share the same rate on a given turn. A Python-integer grid
combines exact weighted turn contributions before safe int64 limb transforms.
This preserves exact rational components but adds memory and arithmetic compared
with the previous boolean-mask grid; no automatic size cutoffs were introduced.

Small benchmark (90 candidates, 729 grid cells, six sources, two costs, five
turns, opening size 3, both positions; tracemalloc enabled): batch construction
was 0.010s without availability discounts vs 0.021s with them. Observed Python
allocation peaks were 0.15/0.13 MiB respectively; these tiny measurements are
noisy and do not predict large-grid memory. The full notebook was not built.
Tests compare physical draw/independent failure enumeration, analytic factors,
new-family pool generation, and scalar/batch rankings and crossings.

Rule references:
- https://mtg.wtf/card/kld/243/Blooming-Marsh
- https://www.mtg.wtf/card/mid/285/Shipwreck-Marsh
- https://www.mtgsalvation.com/cards/universes-beyond-final-fantasy/67833-starting-town


## Joint independent availability replaces separate factors

Only available source copies now contribute both total mana and Hall color
supplies. Source failures remain independent; no play sequences are simulated.
Seen types still enable Verges. Scalar counting keeps its existing state shape,
but updates color coverage by successful count instead of drawn count.

Batch computes the success-payment mask once, then averages along each source
axis with an integer-scaled binomial thinning matrix. It groups equal rate
signatures across turns before the outer draw/composition transform. Typed
sources (basics and shocks) always have availability one in the current catalog,
so Verge enablers in the successful-count mask equal those among all seen lands.
A future unreliable typed source would need a separate seen-type mask; do not
silently reuse this assumption if extending the catalog. Python-integer grids
and safe int64 limbs preserve exact rational components.

Regression: tapped UB plus Mountain for U on T1 is now zero, not one. At T2,
tapped UR plus tapped BG plus Mountain pay UB with probability 1/4. Tests
independently enumerate physical draws, availability outcomes, and color
assignments; all 63 tests pass. Zero costs and existing land rates are unchanged.
Rebuild existing component tables. README and notebook explain joint payment.

Profile: existing 3,144-candidate Sultai reference, 18 costs, T1-T7, both positions.
Two isolated runs per model give medians 11.612s separate vs 10.628s joint.
Detailed measurements and caveats are in reports/joint_availability_profile.md.
Joint grid work increases, but tighter axis-based denominators reduced limb
transform calls from 80 to 46 on this reference. No component increased;
51,893/56,592 decreased. No full notebook build or
peak-memory profiling was performed.


## Baseline-free construction and notebook (2026-11-03)

ComponentTable and build_component_table no longer accept or store a baseline.
Construction depends only on the explicit bounded space, spells, and evaluation
settings. Pass baseline=base to table.rank/scored.rank for query-local deltas
and swaps; those calls validate the base is an evaluated candidate and do not
change absolute ranks or later queries. Crossings defaults to the current winner;
its existing optional baseline argument remains for explicit comparisons.

The notebook has no MANA_BASE or baseline arguments. Its optimum and top-ten
sections show absolute scores and the optimum composition. Sensitivities show
transitions around the current optimum. Land count/colors/family bounds alone
define the complete search. Stale outputs were cleared. Inputs and the entire
report were exercised on a small complete eight-candidate pool without building
the notebook's large selected pool. Comparison helpers remain in the library
and the command-line example illustrates optional query-time comparisons.


## Total reliability feature cost profile (2026-11-03)

Compared current joint reliability with all land rates forced to one on the
3,144-candidate Sultai batch reference: nine source axes, 781,250 grid cells,
18 costs, T1-T7, both positions. Fresh processes, three unprofiled runs per mode,
imports excluded, no concurrent tests. Median build 2.663s off vs
8.786s on (3.30x). Median Windows peak process resident memory
85.1 vs 141.4 MiB. Only Town is unreliable in this pool.
This comparison measures the whole feature, unlike separate-vs-joint profiling.
Joint profile spends 4.246s in weighted grids (including 2.923s availability
transforms) and 2.903s in 46 integer-limb transforms, versus 1.811s/34 transforms
with reliability off. Grid integer arithmetic dominates the added cost, not rate
lookup or candidate enumeration. See reports/land_reliability_cost.md for raw
runs, method, caveats, optimization candidates, and local reproduction artifacts.
No evaluator or notebook behavior was changed by this profiling task.


## Standard pool filter (2026-11-03)

sources_for_colors and ManaSpace.from_colors accept format="standard", using
STANDARD_COLORS and STANDARD_AS_OF in mana_lands. None retains the unrestricted
model. The snapshot admits all basic/shock/Verge/tapped pairs and Town/Cavern;
fast lands admit only the five enemy pairs (WB, WR, UR, UG, BG), slow lands none.
Tapped means a legal untyped representative exists, not a specific named card.
This is explicit dated card knowledge, not a live format/rotation service.
Overrides cannot reintroduce excluded sources. An empty family may make the
requested land count infeasible, using existing bounds validation.

Standard legality evidence checked for the current Sultai question:
https://mtg.wtf/card/otj/266/Blooming-Marsh (legal)
https://mtg.wtf/card/otj/267/Botanical-Sanctum (legal)
https://mtg.wtf/card/one/250/Darkslick-Shores (not legal)
https://mtg.wtf/card/lci/269/Cavern-of-Souls (legal)
https://magic.wizards.com/en/formats/standard
https://magic.wizards.com/en/news/feature/edge-of-eternities-release-notes
https://www.magic.wizards.com/en/news/feature/collecting-lorwyn-eclipsed

Notebook now explicitly sets FORMAT="standard". Current 26-land UBG search with
shock/fast/Verge/Town/Cavern bounds 0-4 becomes 10 sources, 363,165 candidates,
and 9,765,625 grid cells, down from 11 / 2,897,884 / 48,828,125. This removes
Darkslick Shores while retaining Botanical Sanctum and Blooming Marsh. The user
requested a report before continuing profiling; no full notebook profiling was
started during this change.


## Current notebook three-way benchmark (2026-11-03)

Full filtered notebook workload (26 lands, 34 nonlands, UBG, standard snapshot;
shock/fast/Verge/Town/Cavern 0-4, 363,165 candidates, 9,765,625 grid cells,
21 costs, seven turns/both positions/opening seven) was built in fresh sequential
processes. Reliability off: 83.57s / 1.58 GiB peak resident; V1 separate:
219.23s / 2.08 GiB; V2 joint: 378.50s / 2.30 GiB. Single full runs, not medians.
All meet the requested 15-minute build target; report/scoring time is excluded.

Representative three-cost full-grid profiles show equal outer transform counts
for V1/V2 (18), versus 6 off. V2's joint axis transforms add 39.14s in those
profiles, dominating its slower runtime here. There are three unreliable axes
(two fast and Town), unlike the prior one-Town reference. Do not extrapolate the
small reference's V2 speed advantage. Raw inputs/results, implementation hashes,
profile summaries and caveats are in reports/notebook_reliability_profile.md and
its linked artifacts. No evaluator behavior was changed by profiling.


## No-Cavern optima comparison

Removed Cavern from notebook LAND_FAMILIES at the user's request. The same
Standard-filtered UBG/deck setup now has 32,211 candidates and 1,953,125 grid
cells. Full builds: off 8.76s, V1 separate 37.68s, V2 joint 74.80s; scoring/top-ten
selection under one second each. Shock/Town penalties are 0.014/0.01.
All three models have distinct unique optima. V1 optimum ranks 8th under V2,
losing 0.002180735 score; V2 swaps two Blooming Marsh for two BG shocks. Off's
optimum ranks 2,657th under V2, losing 0.036343067. Detailed counts and exact
cross-model scores are in reports/no_cavern_optimization.md and .json.
Crucially, full component tables are now saved in .cache/no_cavern_*_table.pkl,
so later comparisons can be derived without repeating expensive construction.


## Land-model robustness experiments

Used complete no-Cavern pool for 25 penalty settings and four importance/mode
weight settings, reusing exact components. Under V2, V1 optima lost at most
0.113% across penalties and 0.176% across weight cases; off optima lost more in
all 29 scenarios (0.642-2.881% penalties, 0.977-2.296% weights).
A single-failure stress kernel preserving marginals only when k<=T picked the
original V1 winner; original V2 lost 0.043%, off lost 0.904%. This is not full
sequencing and reduces marginal failures for surplus k>T.
A pessimistic no-Verge-secondary endpoint gave only a 0.024% V1/V2 gap but
changed V2's optimum by eight replacements, restoring four Botanical Sanctum.
Thus near-equivalence of V1/V2 score quality is robust over these tests, while
exact land counts and no-Botanical advice depend on remaining assumptions.
Raw scenario results, exact experiment definitions and caveats are in
reports/land_model_robustness.md, robustness_results.json, and
robustness_experiment.py. No production evaluator or notebook defaults changed.


## V1 restored as default

At the user's request, scalar and batch evaluators again use separate per-draw
color coverage and independent total-availability factors (V1). Drawn source
counts contribute colors even when those sources fail availability. Standard
filtering, explicit search inputs, baseline-free construction, new land families,
and the no-Cavern notebook pool remain. README and notebook describe V1; stale
notebook outputs were cleared. Historical V2 reports/results are retained.
A local V2 backend snapshot is in .cache/mana_batch_joint.py; historical benchmark
scripts which assume production is V2 need that archived backend patched in
before rerunning. Original saved component tables remain usable without rebuilding.
The restored scalar was checked exactly against nine saved V1 reference rows;
independent draw/failure enumeration and scalar/batch parity tests cover V1.


## Explicit fixed source counts

ManaSpace.from_colors accepts fixed: Mapping[ManaSource,int]. Eligible sources
may be outside enabled flexible families; fixed entries replace any generated
bounds with (n,n), including zero. They count within land_count. Noninteger,
negative, off-color/format-excluded sources, overlaps with overrides, and
infeasible totals are rejected. Existing overrides remain limited to the
flexible generated pool. Fixed eligibility uses the catalog's canonical sources
(including typed shocks), while direct bounds construction remains available.

Notebook now fixes four Caverns and one Swamp within 26 lands, leaving 21 slots
for Standard-filtered shock/fast/Verge/Town sources. Same V1 model and penalties.
This yields 142,740 candidates and 19,531,250 grid cells. Fixing deck counts
must not remove their draw-count axes: draw uncertainty remains. Tests verify
every candidate, small scalar/batch agreement, eligibility, conflicts, fixed-only
spaces and zero counts. The entire notebook report was exercised on a nine-base
six-land pool with the same fixed cards; no large table was built.


## Supplied Sultai deck and tri-lands (2026-11-07)

Added explicit untyped tapped `tri` family; unfiltered pools generate all ten
triples. Standard filtering admits the five TDM tri-lands, so UBG adds only
Opulent Palace. It supplies one mana, carries no basic land types, and uses
(T-1)/T availability in V1. The dated snapshot is now 2026-11-07.

Evidence checked:
https://magic.wizards.com/en/formats/standard
https://media.wizards.com/ContentResources/WPN/deck_checklists/tdm/MTGTDM_EN_DkCklst.pdf
https://mtg.wtf/card/tdm/264/Opulent-Palace
https://mtg.wtf/card/sos/214/Professor-Dellian-Fel (2BG)
https://mtg.wtf/card/blb/215/Glarb-Calamitys-Augur (BGU)
https://magic.wizards.com/en/news/feature/lorwyn-eclipsed-release-notes

The shared example now matches the user's exact 34-spell / 26-land main deck.
Effect-oriented incarnation profiles deliberately omit mixed evoke payments
which trigger neither colored payoff. Spider-Man's extra colored payments
represent copied incarnation payoffs. Sunderflock's 7UU/2UU/1UU are board
scenarios, not independent cards; their weights normalize. Overlord retains
1B impending-only weighting. Cavern remains unrestricted; full sequencing and
joint color/availability simulation were not added. Availability rates are
computed once per evaluation turn, shared by all costs.

The bounded local search fixes four Caverns and one Swamp, allows zero to two
Palaces, and shares one evaluator across three starts (supplied/zero/two Palace)
with visit budgets 200/150/150. Optional Island and Forest are each capped at
one. No full grid is allocated. See the reproducible example command and report
in README; local-optimum certificates apply only to complete neighborhoods.


## Fixed shock-family sweep (2026-11-08)

Added LocalManaEvaluator family_totals, enforced in evaluation and neighborhood
generation. The shock sweep fixes four Towns/Caverns and one Swamp, allows at
most two Palaces, and compares 8-12 shocks with the existing spell/V1 model.
Each run finished a one-land constrained neighborhood within its 500-visit
budget; combined runtime 85.70s. These are local, not global certificates;
coupled shock/nonshock two-transfer moves are not checked.

Exact representative crossings as shock penalty decreases: 8 -> 9 at
0.010716795; 9 -> 10 at 0.008396344; 10 -> 11 at 0.007141866;
11 -> 12 at 0.004899995. At the existing 0.012 penalty, eight shocks still win.
Town's penalty is constant across these bases. Full bases, exact raw scores,
stopping reasons and intervals are in reports/sultai_shock_sweep.json and .md.
Trusted local component caches are retained in .cache/sultai_shock_sweep.pkl.
All five final bases were independently re-evaluated and constraints/intervals
verified. LaTeX does not render in the main chat environment; use ASCII equations.


## Restless Cottage update (2026-11-08)

The input deck has 34 nonlands and 28 lands. Restored two Dellian Fels and two
Overlords, removed Rapid Rescue. Optimize 26 lands with four Caverns, four
Towns and two Restless Cottages fixed, with zero to two basics total. The seed
cuts one Gloomlake Verge and one Wastewood Verge; these cuts are not fixed.
Cottage uses ManaSource("BG", "tapped"), an untyped tapped source; its creature,
Food and graveyard abilities are excluded. Card text checked at:
https://mtg.wtf/card/woe/258/Restless-Cottage
Added LocalManaEvaluator family_maximums for aggregate basic limits; fixed
family totals still enforce the shock count. Updated 8-10 shock sweep report
in place. Historical Palace report is not a current-deck score.


## Awaken/Glarb update (2026-11-08)

Removed both Overlords, increased Awaken to four and Glarb to two. Main deck
remains 34 spells and 26 lands; BGU profiles total six copies and 1B profiles
total two (Bitter Triumph only). Reran 8-10 shocks with four Caverns, four
Towns and two Cottages fixed, up to two basics combined. All three searches
completed constrained one-land neighborhoods in 90.53 seconds total. The
8-shock result replaces one Gloomlake Verge with one Willowrush Verge relative
to the previous result. Nine and ten shocks retain one Island rather than the
previous basic choices. Crossings: 8/9 at 0.007820833 and 9/10 at 0.006047422.
Updated reports in place; independent scalar reevaluation and constraint/
interval checks passed. Twenty-four targeted tests passed.

## General availability schedules (2026-11-08)

Batch opportunity grids now accept simultaneous distinct rational availability
rates from land_availability(kind, turn). Equal-rate land counts are grouped;
a memoized convolution adds independent lands with successes capped at the
required mana value. Rates 0 and 1 use the same recurrence. Integer masses use
the LCM of rate denominators, preserving exactness through limb transforms.
Current schedules, independent land-drop approximation, and separate color
coverage are unchanged. Schedule changes must patch both modules when testing,
because mana_batch and mana_opportunities import land_availability directly.

Isolated reference-pool benchmark (three repetitions, medians): old full table
11.929 s / grid 2.440 s; general full table 15.238 s / grid 6.153 s. Full results
are exactly equal. Generality costs about 28% overall on this fixture; no
single-fractional-rate special path retained. An 85-candidate four-kind mixed
schedule fixture took 0.0258 s full / 0.0231 s grid (five-run medians) and
matched scalar results exactly. Local reproduction scripts are in ignored
.cache/benchmark_availability.py and .cache/benchmark_mixed_availability.py;
the former uses the ignored .cache/mana_batch_before.py baseline snapshot.

All 16 batch/availability tests pass. The bundled .venv launcher
references a missing user interpreter; run .python/cpython-3.12.13-windows-x86_64-none/python.exe
with PYTHONPATH=.venv/Lib/site-packages in this sandbox.
