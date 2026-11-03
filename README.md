# MTG mana and hand analysis

## Mana opportunities

[The standalone evaluator](mana_opportunities.py) scores a supplied mana base
against casting-cost counts and optional importance weights. It uses only the
Python standard library.

```python
from mana_lands import ManaSource
from mana_opportunities import SpellCost, evaluate

base = {
    ManaSource("U", "basic"): 8,
    ManaSource("B", "basic"): 8,
    ManaSource("UB", "shock"): 6,
    ManaSource("WUBRG", "town"): 2,
    ManaSource("WUBRG", "cavern"): 2,
}
spells = [SpellCost("UU", 12), SpellCost("BB", 21, weight=2), SpellCost("WWBU", 1, weight=0.05)]
result = evaluate(base, spells, shock_penalty=0.01, town_penalty=0.01)
print(result.score)
# Exact unweighted expectations and weighted contributions by cost, turn, position:
print(result.opportunities[0])
```

Each drawn physical copy contributes its weight whenever its cost is payable.
Copies and different costs score independently, even when they cannot all be cast
with the same mana. The score averages T1 through T7 and play/draw equally by
default, then subtracts the per-land shock/Town penalties. Mana shortage remains
in the draw distribution. Zero-weight cards still occupy deck slots.

This measures sustained availability with optimistic land selection. It ignores
sequencing, previously cast spells and Cavern's creature restrictions. Tapped entry
is approximated by independent per-land availability, described below.
Counts describe the actual spell package; weights describe importance. Deck size
is inferred from all land and spell counts. Only ordinary generic and WUBRG costs
are supported. Decklist import is not wired yet.

Run `python -m examples.sultai` for the sample Sultai cost profile and an
illustrative mana base. The [original decklist](resources/decks/evoke_elementals.txt)
is retained as sample input; all Sultai-specific choices live in the example.
See [calculation notes](ideas/knowledge/mana-opportunities.md) for the mathematics.

```sh
python -m unittest -v test_mana_opportunities
python -m doctest mana_opportunities.py
```

## Land availability

For each aggregate draw, compute the probability that the lands which succeed
on availability can jointly pay the spell's generic and colored mana cost.
Every land independently has a uniform assumed play turn from 1 through the
current turn T. Earlier drops have untapped; fast/slow entry assumes one drop
each turn.

| Family | Availability on turn T |
| --- | --- |
| `basic`, `shock`, `verge`, `cavern` | 1 |
| `town`, `fast` | 1 through T3, then (T-1)/T |
| `slow` | 0 on T1, 1/2 on T2, then 1 |
| `tapped` | (T-1)/T |

`ManaSource("BG", "fast")` represents Blooming Marsh;
`ManaSource("UB", "slow")` represents Shipwreck Marsh. `tapped` duals are
identified only by their two colors. Each new family supports all ten pairs,
has no basic land types or extra composition penalty, and is an explicit opt-in
in `ManaSpace.from_colors(..., families={"fast": (0, 4), ...})`.
`mana_lands.land_availability(kind, turn)` exposes the exact per-land rate.

Only available lands contribute mana and colors to the payment check. For
example, a tapped UB dual and a Mountain cannot pay U on T1; the Mountain cannot
substitute for the unavailable blue source. Surplus lands compensate only if
the available sources can satisfy the whole cost. Verge enabling still uses
basic land types among all lands seen. These assumptions do not describe an
actual land sequence:
four Towns on T4 give an MV4 opportunity factor of (3/4)^4 = 81/256.
One Town and three basics instead give 3/4; two tapped duals give an MV1 factor
of 3/4 on T2. Zero-cost spells have factor one. There is no fractional mana.
Life is assumed paid for shocks; configured shock/Town penalties still apply.

Rebuild component tables after this change. Scalar and batch components remain
exact fractions; batch calculation now needs a Python-integer weighted grid
before safe integer-limb transforms. Separable binomial transforms average
successful source counts along each source axis, avoiding enumeration of all
combinations of independent failures. Unreliable sources add time and memory
cost on large pools.

## Verge sources and land types

`ManaSource("UB", "verge")` represents Gloomlake Verge: U unconditionally,
B with an Island or Swamp. `mana_lands.VERGE_RULES` covers all ten color pairs,
including their asymmetric primary and secondary production.

Basics infer their own land type. Shocks are untyped unless explicitly declared,
for example `ManaSource("UG", "shock", types="UG")` for a Forest/Island shock.
Town, Cavern, and Verges carry no basic land types. Enablers must be among the
lands seen so far. They need not fit within the turn's land drops, an
optimistic approximation that deliberately ignores enabler sequencing.
Verges have no composition penalty beyond their conditional production.

The command-line example's reference pool fixes one Swamp and excludes Islands/Forests.
Each typed shock, Verge, Starting Town, and Cavern ranges from 0?4. This gives
3,144 legal 26-land bases. Town and Cavern are separate unrestricted rainbow
sources; Cavern restrictions remain excluded. Cavern has no composition penalty.
The notebook starts `shock_penalty` and `town_penalty` at 0.01 each, independently
editable. Search scans every legal composition within the bounds.

The notebook explicitly selects 26 lands in UBG, with 0?3 of each selected basic
and 0?4 of each shock, Verge, Town, and Cavern. No baseline is defined in the notebook. Candidate count and batch capacity-grid size are printed
before exhaustive construction; adding colors or families can increase both sharply.


## Alternate casting costs

Keep physical copies separate from payment options:

```python
from mana_opportunities import CastingMode, Spell

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

## Mana-base search and crossings

Open [sultai_explorer.ipynb](sultai_explorer.ipynb) in PyCharm or Jupyter. Definitions
and bounds are notebook-local. Build the full component table once, then edit
shock/Town penalties and rerun the report. The notebook needs IPython and tqdm;
NumPy accelerates table construction. The scalar evaluator remains a reference.

```python
from mana_search import ManaSpace, build_component_table

space = ManaSpace.from_colors(26, "UBG", families={
    "basic": (0, 3), "shock": (0, 4), "verge": (0, 4),
    "town": (0, 4), "cavern": (0, 4),
})
table = build_component_table(space, spells)
scored = table.score(shock_penalty=0.01, town_penalty=0.01)
top = scored.rank(limit=10)
winner = dict(zip(space.sources, top[0].counts))
shock_change = scored.crossings("shock_penalty", baseline=winner)
town_change = scored.crossings("town_penalty", baseline=winner)
```

Families are explicit opt-ins. Basics use the selected colors; shocks and Verges
use pairs entirely within them. Generated shocks carry both basic land types.
Town and Cavern offer all five colors; Town additionally has its availability discount. Colors are not derived
from spells or the reference base, and do not require every candidate to produce
every selected color. `overrides={source: (minimum, maximum)}` replaces bounds
for individual selected sources; direct `ManaSpace(bounds, land_count)` remains
available for custom pools. Land definitions live in `mana_lands`.

Use `format="standard"` in `ManaSpace.from_colors(...)` to filter sources using
the dated `mana_lands.STANDARD_AS_OF` snapshot (2026-11-03). The notebook enables
this explicitly. Sultai fast lands are Blooming Marsh (BG) and Botanical Sanctum
(UG); Darkslick Shores (UB) is excluded. Unfiltered construction remains available
with `format=None`, the default. Unsupported format names are rejected. The
snapshot must be updated after rotations or relevant reprints; it does not query
a card service at runtime. Abstract tapped duals represent a legal untyped dual
for each pair, without adding card-specific abilities.

All search is exhaustive within the supplied bounds. There is no search-mode
switch or neighborhood search. `backend="auto"` attempts the NumPy batch backend
without size cutoffs; `backend="scalar"` evaluates all bases independently.
Missing NumPy or an unsafe integer-transform bound can select scalar. Memory
allocation errors propagate. Batch probability calculations are exact integer
binomial transforms; no float approximation is introduced.

`progress=` wraps candidate row assembly (per-base evaluation in scalar).
`component_progress=` wraps expensive cost-column transforms in batch. The
notebook supplies tqdm; library code has no UI dependency.

A component table holds mean opportunities per cost, separate shock/Town counts,
and default importance weights. Canonical-equivalent costs share a column;
mode-copy shares and importance reproduce the scalar evaluator. Override cost
importance using `table.score(weights={"UU": 2}, ...)`.

The first score prepares cached integer columns with a common denominator per
cost. Weighted scores then use integer dot products with one score denominator.
A score snapshot is reused for ranking and every crossing query. `rank(limit=10)`
selects ten winners without sorting the full pool or constructing unused swap
records. The optional limit changes displayed results only; every candidate is
scored and participates in crossings. Omit it for a complete ranking.

`scored.crossings("UU")`, `scored.crossings("shock_penalty")`, and
`scored.crossings("town_penalty")` vary one absolute nonnegative parameter.
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

## Generic hand experiments

Compute the exact expected value of your own `Counter[TCard] -> float` function over unordered hands,
then optimize integer deck compositions. `TCard` can be any hashable type. The supplied immutable `Card`
has a name, mana value, and role tags; a multi-role card is still drawn only once.

```python
from hands import expected_score

deck = {"land": 24, "threat": 20, "interaction": 16}
value = expected_score(deck, lambda hand: 2 <= hand["land"] <= 4 and hand["threat"] > 0)
```

This sums multivariate hypergeometric probabilities over every feasible hand, without replacement.
It is exact enumeration with floating-point arithmetic. Scorers must be deterministic and return finite
numbers; Boolean scorers give event probabilities. There is no sequencing or gameplay assumption.

## Run the comparison

The development setup uses the neighboring `../leitwerk` checkout as an editable dependency:

```sh
uv sync
uv run python experiment.py
uv run python experiment.py --budget 100 --seed 0 --seed 1
uv run python -m unittest -v
```

`experiment.py` contains the card types and the example hand scorer. Its rewards and count bounds are
illustrative preferences, not inferred from `rock-mid.txt` or calibrated win rates. Edit those Python
definitions to explore other roles, costs, or synergies. No automatic card lookup is performed.

`--config experiment.json` accepts overrides for `size`, `minimum`, `maximum`, `initial`, `hand_size`,
`budget`, and `seeds`. Count arrays follow the card order printed in the first output line. For example:

```json
{"budget": 100, "seeds": [0, 1], "initial": [24, 12, 6, 12, 6]}
```

Both methods receive the same initial deck and unique-evaluation budget, with separate ordered-tuple
caches. Discrete search tests single-card transfers and restarts at local optima. Leitwerk maximizes the
same exact score, decoding preferences through capped proportional allocation and largest-remainder
rounding. Ties follow the fixed input order. Minimum counts are allocated first.

Each JSON result reports the baseline score, best composition and score, unique evaluations, proposal
count, elapsed seconds, and stopping reason. A cap of 20 proposals per budgeted evaluation prevents
duplicate proposals from running forever; a method may stop below its evaluation budget. Neither
method guarantees the global optimum. The tests compare both with an exhaustively solved tiny case.

Enumeration grows combinatorially with the number of types and hand size. Start with a few broad
types; the example prints its initial feasible-hand count. This iteration excludes mulligans, color,
tapped lands, sideboards, and playouts.

The notebook report shows the optimum first, then the top ten candidates with
separate OUT/IN columns, casting-cost weight sensitivities for every cost, and
finally shock/Town penalty sensitivities. All use the same score snapshot.
