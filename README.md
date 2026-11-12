# MTG mana and hand analysis

## Development

Run `uv sync` to install the package and its dependencies in an editable environment.
Run commands below from the repository root; notebooks should use this environment's
Python kernel. Notebook support (Jupyter/IPython) must be installed separately.

```sh
uv run python -m unittest discover -s tests -v
uv run python -m examples.experiment --budget 1 --seed 0
```

Reusable code lives in `src/mtg_tools/`. `tests/` holds
the test suite, `examples/` the deck-specific workflows, `notebooks/` interactive
analyses, and `resources/` sample inputs. Maintained calculation guides live in
`docs/`; `ideas/` holds workbench notes and historical results in `ideas/reports/`.
Examples and resources are checkout assets and are not included in the installed
package. Old top-level imports are replaced by `mtg_tools.<module>` imports.

Mana analysis lives in `mtg_tools.mana`:

| Modules | Responsibility |
| --- | --- |
| `lands`, `spells` | Source definitions, land catalog, costs, and casting profiles |
| `model`, `policy` | Production interfaces and compilation; explicit heuristic assumptions |
| `timing`, `payment`, `evaluation`, `_batch` | Turn weighting, payment probabilities, scalar/cached evaluation, and batch acceleration |
| `space` | Bounds, validation, enumeration, and legal replacement neighborhoods |
| `local` | Visit budgets, local optimization, and stopping certificates |
| `tables`, `sensitivity` | Component tables, weighted ranking, and exact weight transitions |

`mtg_tools.hands` and `mtg_tools.search` remain the separate generic hand-scoring
workflow. Decklist import depends on spell profiles rather than the evaluator.
Use `mtg_tools.mana` modules for mana imports. Regenerate saved pickle objects
that reference the former flat module paths.

## Mana opportunities

[The standalone evaluator](src/mtg_tools/mana/evaluation.py) scores a supplied mana base
against casting-cost counts and optional importance weights. It uses only the
Python standard library.

```python
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.spells import SpellCost
from mtg_tools.mana.evaluation import evaluate
from mtg_tools.mana.policy import heuristic_mana_model

base = {
    ManaSource("U", "basic"): 8,
    ManaSource("B", "basic"): 8,
    ManaSource("UB", "shock"): 6,
    ManaSource("WUBRG", "town"): 2,
    ManaSource("WUBRG", "cavern"): 2,
}
spells = [SpellCost("UU", 12), SpellCost("BB", 21, weight=2), SpellCost("WWBU", 1, weight=0.05)]
model = heuristic_mana_model()
result = evaluate(base, spells, model=model)
print(result.score)
# Exact unweighted expectations and weighted contributions by cost, turn, position:
print(result.opportunities[0])
```

Each drawn physical copy contributes its weight whenever its cost is payable.
Copies and different costs score independently, even when they cannot all be cast
with the same mana. The score averages T1 through T7 and play/draw equally by
default. Composition constraints are supplied separately as search-space bounds. Mana shortage remains
in the draw distribution. Zero-weight cards still occupy deck slots.

This measures sustained casting opportunities without land-drop sequencing or
previously cast spells. An explicit model supplies production outcomes and a
per-turn source limit. The example policy treats Cavern as unrestricted rainbow
mana and approximates tapped entry through independent per-land availability.
Counts describe the actual spell package; weights describe importance. Deck size
is inferred from all land and spell counts. Only ordinary generic and WUBRG costs
are supported. Import printed nonland costs with the notebook below.

Run `python -m examples.sultai` for the sample Sultai cost profile and an
illustrative mana base. The [original decklist](resources/decks/evoke_elementals.txt)
is retained as sample input; all Sultai-specific choices live in the example.
See [calculation notes](docs/mana-opportunities.md) for the mathematics.

```sh
python -m unittest discover -s tests -p "test_mana_opportunities.py" -v
python -m doctest src/mtg_tools/mana/evaluation.py
```

## Decklist import

Open [decklist_import.ipynb](notebooks/decklist_import.ipynb), replace `DECKLIST`, and run all
cells. The supplied Dimir example queries Scryfall and prints a copyable `SPELLS`
tuple of `SpellCost` entries with card-name comments. It also leaves `SPELLS`
available in the kernel for evaluation with a separately supplied mana base.

```python
from mtg_tools.decklist_import import import_decklist, format_spells

imported = import_decklist("4 Spyglass Siren (LCI) 78\n4 Island (ZNR) 381")
SPELLS = imported.spells
print(format_spells(imported))
# SPELLS = (
#     SpellCost('U', 4),  # Spyglass Siren
# )
```

Input accepts positive quantities followed by names, optional `(SET) number`
annotations, blank lines, and an optional `Deck` heading. The `Sideboard` section
is excluded. Exact card/front-face names are matched case-insensitively; printing
annotations and format legality are ignored. Duplicate cards combine in first
appearance order; different cards with the same cost remain separate, all at
weight 1. Every resolved land is excluded, including unsupported utility lands.

Only the printed front/main cost is used for transforming cards, modal
double-faced cards, adventures, and flip cards. Alternate costs and back faces
are ignored. Split cards, missing mana costs, and costs containing X, hybrid,
Phyrexian, snow, or required colorless mana produce diagnostics. `{0}` is supported.
Unresolved names also fail the import: no partial spell package is returned.
The notebook clears earlier `SPELLS` before querying to avoid stale results.

Each import makes fresh batched requests to the [Scryfall API](https://scryfall.com/docs/api),
requires internet access, and saves no catalog or cache. The notebook output
records the successful conversion, rather than a full card database. No land
model or format validation is generated. Run the offline tests with
`python -m unittest discover -s tests -p "test_decklist_import.py" -v`.

## Land availability

Every evaluation and search constructor requires `model=`. `heuristic_mana_model()`
is an explicit policy choice: a land's output succeeds at its turn-based rate,
otherwise it produces nothing. Each realized source must supply both its mana
and its colors. There is no separate color-coverage discount.

The heuristic assumes a uniform play turn from 1 through the current turn T.
Earlier drops have untapped; fast/slow entry assumes one drop each turn. The
policy allows at most T sources in a payment, without choosing a land-drop order.

| Family | Availability on turn T |
| --- | --- |
| `basic`, `shock`, `verge`, `cavern` | 1 |
| `town`, `fast` | 1 through T3, then (T-1)/T |
| `slow` | 0 on T1, 1/2 on T2, then 1 |
| `tapped`, `tri` | (T-1)/T |

`ManaSource("BG", "fast")` represents Blooming Marsh;
`ManaSource("UB", "slow")` represents Shipwreck Marsh. `tapped` duals are
identified only by their two colors. Each new family supports all ten pairs,
has no basic land types or extra composition cost, and is an explicit opt-in
in `ManaSpace.from_colors(..., families={"fast": (0, 4), ...})`.
`mtg_tools.mana.policy.land_availability(kind, turn)` exposes the exact per-land rate.

An unavailable source supplies neither mana nor colors. A tapped UB dual and
a Mountain cannot pay U on T1. Surplus drawn lands can compensate only when the
successful sources can actually pay the cost. Four Towns on T4 give an MV4
opportunity factor of (3/4)^4 = 81/256. Zero-cost spells remain payable.
Life is assumed paid for shocks; life totals are not simulated.

Customize the heuristic with `availability(source, turn)` and `source_limit(turn)`
callables. A source limit of `None` removes the turn-based cap. Availability can
use any exact rate from zero to one, with different simultaneous rates per source.

For different production rules, supply a `ManaModel` directly:

```python
from fractions import Fraction
from mtg_tools.mana.model import ManaModel, ManaOutcome

model = ManaModel(
    outcomes=lambda source, context: (
        ManaOutcome(Fraction(2, 3), ("U", "B")),
        ManaOutcome(Fraction(1, 3), ("",)),
    ),
    source_limit=lambda turn: turn,
)
```

This illustrative model treats every source as a 2/3 chance of one mana chosen
from U or B. Entries in `options` are alternative bundles, not random color
choices: `("U", "B")` offers one mana; `("UB",)` would offer two together and
is explicitly unsupported in this version. `("",)` produces nothing.
Probabilities must sum to one; duplicate outcomes are merged.

`context` exposes `turn` and the basic land types among lands seen (`seen_types`).
Outcomes are independent conditional on that context. Callbacks must be pure;
configuration is compiled before the hot loops. The evaluator contains no
card-family production rules. Larger mana bundles will require extending payment
calculation, but retain the same model interface.

Scalar and batch results remain exact fractions. Batch evaluation groups residual
payment requirements and identical uncertain sources before integer-limb transforms.
Local evaluators compile the policy once and reuse their component cache.
Persist `evaluator.cache_signature` with `dict(evaluator.cache)` and restore with
`evaluator.restore_cache(signature, entries)`; incompatible policy/draw configurations
are rejected. Tables also carry `model_signature`. Rebuild old tables and caches;
historical reports retain their original scoring assumptions.

## Verge sources and land types

`ManaSource("UB", "verge")` represents Gloomlake Verge: U unconditionally,
B with an Island or Swamp. `mtg_tools.mana.lands.VERGE_RULES` covers all ten color pairs,
including their asymmetric primary and secondary production.

Basics infer their own land type. Shocks are untyped unless explicitly declared,
for example `ManaSource("UG", "shock", types="UG")` for a Forest/Island shock.
Town, Cavern, and Verges carry no basic land types. Enablers must be among the
lands seen so far. They need not fit within the turn's land drops, an
optimistic approximation that deliberately ignores enabler sequencing.
Verge conditional production is modeled directly.

The reduced exhaustive command-line example fixes one Swamp, excludes
Islands/Forests, and uses the source families present in the shared reference
base. Palace ranges from 0-2; other nonbasic sources range from 0-4.

The exhaustive explorer selects 26 lands in UBG, fixing four Caverns and one
Swamp. Its flexible pool retains shocks, fast lands, Verges, Town, and optional
Island/Forest, without tri-lands enabled. It prints candidate and capacity-grid
sizes before construction. The Palace optimization uses the bounded local
notebook described below, avoiding this large grid. Fixed deck counts retain
draw uncertainty, so their batch axes are still needed.



## Alternate casting costs

Keep physical copies separate from payment options:

```python
from mtg_tools.mana.spells import CastingMode, Spell

spell = Spell(count=4, modes=(CastingMode("UU"), CastingMode("BB")), weight=1)
```

Mode weights normalize within each profile (uniform by default). This profile
occupies four deck slots, not eight. Each mode contributes half the profile's
importance when payable; both together contribute the full importance. Mode
weights may be zero, but their sum must be positive. `SpellCost` remains the
single-mode shorthand with identical results. Both input types may be mixed.
Reported `expected_copies` are normalized mode-copy opportunities when profiles
have multiple modes. Search tables retain these normalized shares per cost;
default cost weights reproduce profile importance, and overrides replace the
importance for that cost's shares. Rebuild a table to change mode shares.

## Half-life turn weighting

`evaluate`, `LocalManaEvaluator`, and `build_component_table` accept
`half_life=h` and `tail_tolerance=0.05`. Omit `turns` when using decay.
Without decay, `turns` still selects a uniform horizon and defaults to seven.

On turn n the raw weight is `2**(-(n-1)/h)`. The horizon H is the smallest
positive integer for which `2**(-H/h) < tail_tolerance`. Thus h=2 uses nine
turns (4.42% omitted weight), and h=3 uses thirteen (4.96%). A strict inequality
applies even at exact tail boundaries. The scalar and batch backends use the
same weights. Play and draw remain equally weighted.

Raw exponential weights are rounded to integer multiples of 1e-9, then
normalized as exact fractions over the retained horizon. Payment probabilities
remain exact; the exponential weighting is a numerical approximation. Scores
are normalized weighted means of casting opportunities.
Per-turn opportunity rows remain unweighted; consumers aggregating these rows
must use the timing weights rather than divide by the number of turns.
`resolve_timing` in `mtg_tools.mana.timing` exposes the resolved horizon, weights, omitted
mass and signature; local evaluators expose this as `.timing`. Table metadata
includes `timing_signature`. Cache signatures include timing configuration;
old caches must be rebuilt.

The tail threshold bounds omitted weight, not relative score error or changes
to the winning base. Decay does not change land sequencing assumptions or
casting-mode importance. Keep full casting profiles when replacing a hard
cutoff: dropping expensive modes redistributes importance toward cheap ones.

Run `python -m examples.moonshadow_decay` for full-profile h=2 and h=3 local
searches with raw scoring and explicit composition bounds. This preserves the exact
34-spell/26-land Moonshadow list, fixes four Caverns and four Towns, caps basics
at two, and explicitly adds Sultai slowlands to the previous Standard-filtered
pool. Three supplied starts and the strongest cached base share components for each half-life. Budget-limited searches
resume with doubled budgets until a complete two-land neighborhood is checked.
Reports and importable 60-card decklists are saved as
`ideas/reports/moonshadow_decay_h2.*` and `ideas/reports/moonshadow_decay_h3.*`.
Slowland legality is outside the pool's Standard snapshot; Cavern restrictions
and land sequencing remain unmodeled. These are local, not global optima.

## Mana-base search and crossings

Open [sultai_explorer.ipynb](notebooks/sultai_explorer.ipynb) in PyCharm or Jupyter. Definitions
and bounds are notebook-local. Build the full component table once, then edit
casting-cost importance weights and rerun the report. The notebook needs IPython and tqdm;
NumPy accelerates table construction. The scalar evaluator remains a reference.
Set `TURNS` in the notebook's build cell to choose the horizon (default 7).
Changing it requires rebuilding: table components already average turns 1 through `TURNS`.

```python
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.tables import build_component_table

space = ManaSpace.from_colors(26, "UBG", format="standard", families={
    "shock": (0, 4), "fast": (0, 4), "verge": (0, 4), "town": (0, 4),
}, fixed={ManaSource("WUBRG", "cavern"): 4, ManaSource("B", "basic"): 1},
   family_bounds={"shock": (8, 12), "town": (0, 4), "basic": (1, 1)})
table = build_component_table(space, spells, model=model)
scored = table.score()
top = scored.rank(limit=10)
winner = dict(zip(space.sources, top[0].counts))
cost_change = scored.crossings(table.costs[0], baseline=winner)
```

Families are explicit opt-ins. Basics use the selected colors; shocks and Verges
use pairs entirely within them. Generated shocks carry both basic land types.
Town and Cavern offer all five colors; Town additionally has its availability discount. Colors are not derived
from spells or the reference base, and do not require every candidate to produce
every selected color. `overrides={source: (minimum, maximum)}` replaces bounds
for individual selected sources; direct `ManaSpace(bounds, land_count)` remains
available for custom pools. Land definitions live in `mtg_tools.mana.lands`.

`fixed={source: count}` adds eligible sources even when their families are absent
from the flexible pool, or replaces their individual source bounds with exact counts; aggregate family bounds still apply.
These counts occupy slots within `land_count`; they are not extra lands.
Zero fixes a source at zero. Counts must be nonnegative integers, and fixed
sources must satisfy the selected colors and format. A source cannot appear
in both `fixed` and `overrides`; infeasible totals are rejected.

Use `format="standard"` in `ManaSpace.from_colors(...)` to filter sources using
the dated `mtg_tools.mana.lands.STANDARD_AS_OF` snapshot (2026-11-07). The notebook enables
this explicitly. Sultai fast lands are Blooming Marsh (BG) and Botanical Sanctum
(UG); Darkslick Shores (UB) is excluded. Unfiltered construction remains available
with `format=None`, the default. Unsupported format names are rejected. The
snapshot must be updated after rotations or relevant reprints; it does not query
a card service at runtime. Abstract tapped duals represent a legal untyped dual
for each pair, without adding card-specific abilities.

Component-table search is exhaustive within the supplied bounds. The separate
local-search API evaluates bounded neighborhoods without a component table. `backend="auto"` attempts the NumPy batch backend
without size cutoffs; `backend="scalar"` evaluates all bases independently.
Missing NumPy or an unsafe integer-transform bound can select scalar. Memory
allocation errors propagate. Batch probability calculations are exact integer
binomial transforms; no float approximation is introduced.

`progress=` wraps candidate row assembly (per-base evaluation in scalar).
`component_progress=` wraps expensive cost-column transforms in batch. The
notebook supplies tqdm; library code has no UI dependency.

A component table holds mean opportunities per cost and default importance weights. Canonical-equivalent costs share a column;
mode-copy shares and importance reproduce the scalar evaluator. Override cost
importance using `table.score(weights={"UU": 2}, ...)`.

The first score prepares cached integer columns with a common denominator per
cost. Weighted scores then use integer dot products with one score denominator.
A score snapshot is reused for ranking and every crossing query. `rank(limit=10)`
selects ten winners without sorting the full pool or constructing unused swap
records. The optional limit changes displayed results only; every candidate is
scored and participates in crossings. Omit it for a complete ranking.

`scored.crossings("UU")` varies that absolute nonnegative casting-cost weight.
Parallel lines are reduced to the best representative for each exact slope;
this preserves the global envelope. Integer inequalities produce exact closed
optimality intervals and immediate successors. At simultaneous crossings, the
outward winning slope wins, then fewest replacements, then canonical count order.
Only actual successors get OUT/IN descriptions; no per-candidate comparison
objects are materialized. A nonoptimal reference can have an interval elsewhere,
but receives no next-optimum transitions at the current settings.

Convenience methods `table.rank(...)` and `table.crossings(...)` remain; use an
explicit `scored = table.score(...)` snapshot to share scoring work across queries.
Tables contain no baseline. Rankings return absolute scores by default; pass
`baseline=base` to `scored.rank(...)` or `table.rank(...)` for optional deltas
and swaps. Crossings default to the current winner; an explicit `baseline=base`
queries another evaluated candidate without changing the table. Results cover the full bounded pool, not unrestricted bases.

Run `python -m examples.sultai_search` for the reduced reference-pool example and
separate table-build/report timings.

### Local search completion checks

`local_search` defaults to `max_replacements=2`. It first takes improving
one-land moves until none remain. It then checks every legal one- or two-land
replacement. An improving two-land move resumes one-land descent, followed by
another completion check. It does not check two-land moves at every descent step.

A complete final check returns `stopped="two-land local optimum"`; this is not a
global optimum certificate. Set `max_replacements=1` for the former cheaper
behavior and `stopped="one-land local optimum"`. The default 500-visit budget is
unchanged. Both phases share the budget and component cache, and repeated bases
count only once within a run (cache hits from earlier runs still count as visits).
If the completion check or subsequent descent runs out of budget, the best base
found is returned with `stopped="evaluation budget"`, without a certificate.
Larger neighborhoods can therefore require a larger budget to finish.

`ManaSpace.neighbor_counts(base, max_replacements=1)` exposes the sorted,
deduplicated eligible compositions without scoring. `mtg_tools.mana.local.value_and_swap_deltas`
accepts the same keyword, defaulting to one-land moves for direct callers.
Two-land generation checks constraints on the final composition, allowing
coupled moves that preserve an exact family total despite individually illegal
transfers. Source bounds, fixed lands and aggregate family bounds apply
in both phases. The landscape experiment uses this shared generator.

## Generic hand experiments

For the supplied Sultai deck, open [sultai_local_search.ipynb](notebooks/sultai_local_search.ipynb)
or run `python -m examples.sultai_optimize`. Both use the shared deck in
`examples.sultai`: 34 spells and 26 lands, with four Caverns, four Towns, and two Restless Cottages fixed.
Standard-filtered shocks, fast lands, Verges, and Town range from 0-4; Island
and Forest are flexible, with at most two basics total; Opulent Palace ranges from 0-2. The supplied base and variants
with zero and two Palaces use budgets of 200, 150, and 150 visited bases.
All starts share cached exact components. No global grid is constructed.

The evaluator averages
turns 1-7 and play/draw, with opening seven. Incarnation profiles target enters
effects, Spider-Man includes copying payoff scenarios, and Sunderflock includes
7UU/2UU/1UU scenarios. Physical copies count once and modes share importance
uniformly. The current package has four Awaken and two Glarb, without Overlords. These are opportunity assumptions;
board presence, sequencing, and Cavern restrictions are not simulated.

The command writes named land counts, OUT/IN changes, score comparisons,
per-cost contributions, timings, and per-run stopping reasons to
`ideas/reports/sultai_palace_optimization.json` and `.md`. Use `--output PATH.json`
to choose another output location. Search is deterministic and bounded;
results distinguish budget stops from fully checked two-land local optima,
without certifying a global optimum.

### Tapped tri-lands

`ManaSource("UBG", "tri")` represents Opulent Palace: one mana in any of its
three colors, no basic land types, and the same availability rule as `tapped`.
It cannot enable Verges. Opt in with `families={"tri": (0, 2), ...}`.
Unrestricted generation supports all ten triples; Standard filtering includes
only Mystic Monastery, Nomad Outpost, Sandsteppe Citadel, Opulent Palace, and
Frontier Bivouac in the November 7, 2026 snapshot. Only Palace fits UBG.
`mtg_tools.mana.lands.TRI_NAMES` maps those canonical triples to card names. This models
the untyped tapped tri-lands, not typed Triomes or lands with extra abilities.
Legality evidence: [current Standard sets](https://magic.wizards.com/en/formats/standard)
and [TDM checklist](https://media.wizards.com/ContentResources/WPN/deck_checklists/tdm/MTGTDM_EN_DkCklst.pdf).

Compute the exact expected value of your own `Counter[TCard] -> float` function over unordered hands,
then optimize integer deck compositions. `TCard` can be any hashable type. The supplied immutable `Card`
has a name, mana value, and role tags; a multi-role card is still drawn only once.

```python
from mtg_tools.hands import expected_score

deck = {"land": 24, "threat": 20, "interaction": 16}
value = expected_score(deck, lambda hand: 2 <= hand["land"] <= 4 and hand["threat"] > 0)
```

This sums multivariate hypergeometric probabilities over every feasible hand, without replacement.
It is exact enumeration with floating-point arithmetic. Scorers must be deterministic and return finite
numbers; Boolean scorers give event probabilities. There is no sequencing or gameplay assumption.

## Run the experiment

Install dependencies and run the discrete search experiment:

```sh
uv sync
uv run python -m examples.experiment
uv run python -m examples.experiment --budget 100 --seed 0 --seed 1
uv run python -m unittest discover -s tests -v
```

`examples/experiment.py` contains the card types and the example hand scorer. Its rewards and count bounds are
illustrative preferences, not inferred from `rock-mid.txt` or calibrated win rates. Edit those Python
definitions to explore other roles, costs, or synergies. No automatic card lookup is performed.

`--config experiment.json` accepts overrides for `size`, `minimum`, `maximum`, `initial`, `hand_size`,
`budget`, and `seeds`. Count arrays follow the card order printed in the first output line. For example:

```json
{"budget": 100, "seeds": [0, 1], "initial": [24, 12, 6, 12, 6]}
```

Discrete search tests single-card transfers and restarts at local optima. Random restarts
use capped proportional allocation and largest-remainder rounding, allocating minimums first.

Each JSON result reports the baseline score, best composition and score, unique evaluations, proposal
count, elapsed seconds, and stopping reason. A cap of 20 proposals per budgeted evaluation prevents
duplicate proposals from running forever; search may stop below its evaluation budget. Search does not guarantee the global optimum. Tests compare it with an exhaustively solved tiny case.

Enumeration grows combinatorially with the number of types and hand size. Start with a few broad
types; the example prints its initial feasible-hand count. This iteration excludes mulligans, color,
tapped lands, sideboards, and playouts.

The notebook report shows the optimum first, then the top ten candidates with
separate OUT/IN columns and casting-cost weight sensitivities for every cost,
all using the same score snapshot.


## Fixed shock-count comparisons

Run `python -m examples.sultai_shock_sweep` to optimize exactly 8, 9 and 10 shocks
independently with the shared Sultai deck. Four Towns, four Caverns and two Cottages
remain fixed; basics total at most two and Palace at most two. Each run has a
500-visit budget. The report distinguishes completed checks from budget stops.

`python -m examples.moonshadow_fixed_landscape` performs the h=2 Moonshadow
comparison at exactly 8 through 12 shocks. Use `--count 10` for one count and
`--merge` to render existing per-count results without rerunning searches.
Reports contain directly comparable scores, marginal gains, constraints,
stopping reasons and full decklists. Existing fixed-count raw results retain
their original search provenance because their objective has not changed.

## Aggregate composition constraints and score schema

Every score is a normalized weighted casting-opportunity score. There are no
composition deductions, and life loss is not simulated. Constraints restrict
eligibility without changing a base's score. Compare scores only when the spell
profiles, importance weights, timing and mana model are the same.

Use `ManaSpace(bounds, land_count, family_bounds=...)` or pass `family_bounds`
to `ManaSpace.from_colors`. For example, `{'shock': (8, 12), 'town': (4, 4),
'basic': (0, 2)}` allows eight through twelve shocks, exactly four Towns and at
most two basics across all colors. A fixed count is `(n, n)`. These bounds are
aggregate; the existing `families` argument assigns bounds to each individual
source. Both apply, along with `fixed` and per-source overrides.

Direct validation, exact candidate counting, exhaustive enumeration, scalar and
batch tables, and both local-search phases use the same space. Family bounds
are immutable, must name a selected family and must be jointly feasible with
source bounds and the total land count. Omitted bounds leave a family unrestricted
within its source capacities. Aggregate bounds reduce candidate counts but do
not necessarily reduce the batch capacity grid.

Evaluation and ranking results expose only `score`. Local/table scores are exact
fractions; standalone evaluation returns a float. Casting-cost weight overrides
and their sensitivity intervals remain available. Old result/table pickle schemas
and old local-cache signatures are rejected explicitly; regenerate them. The
removal inventory is in [ANALYSIS_MIGRATION.md](ideas/ANALYSIS_MIGRATION.md).
