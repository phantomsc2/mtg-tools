# MTG mana and hand analysis

## Mana opportunities

[The standalone evaluator](mana_opportunities.py) scores a supplied mana base
against casting-cost counts and optional importance weights. It uses only the
Python standard library.

```python
from mana_opportunities import ManaSource, SpellCost, evaluate

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
sequencing, previously cast spells, tapped entry and Cavern's creature restrictions.
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

## Verge sources and land types

`ManaSource("UB", "verge")` represents Gloomlake Verge: U unconditionally,
B with an Island or Swamp. `VERGE_RULES` also supports Wastewood (BG: G first,
conditional B) and Willowrush (UG: U first, conditional G).

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

The notebook additionally allows 0–2 of each basic type (W/U/B/R/G), starting
with one Swamp and zero other basics. Its expanded pool contains 4,581,982 bases
and uses the batch backend for exhaustive builds without size cutoffs.
Search covers the entire bounded pool.


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

space = ManaSpace({source: (0, 4) for source in base}, land_count=26)
table = build_component_table(space, spells, baseline=base)
scored = table.score(shock_penalty=0.01, town_penalty=0.01)
top = scored.rank(limit=5)
winner = dict(zip(space.sources, top[0].counts))
shock_change = scored.crossings("shock_penalty", baseline=winner)
town_change = scored.crossings("town_penalty", baseline=winner)
```

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
A score snapshot is reused for ranking and every crossing query. `rank(limit=5)`
selects five winners without sorting the full pool or constructing unused swap
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
Crossings default to the supplied starting baseline, or the current winner when
none was supplied. Results cover the full bounded pool, not unrestricted bases.

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
