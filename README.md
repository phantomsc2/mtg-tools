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
    ManaSource("UB", "dual"): 6,
    ManaSource("WUBRG", "rainbow"): 4,
}
spells = [SpellCost("UU", 12), SpellCost("BB", 21, weight=2), SpellCost("WWBU", 1, weight=0.05)]
result = evaluate(base, spells, dual_penalty=0.01, rainbow_penalty=0.02)
print(result.score)
# Exact unweighted expectations and weighted contributions by cost, turn, position:
print(result.opportunities[0])
```

Each drawn physical copy contributes its weight whenever its cost is payable.
Copies and different costs score independently, even when they cannot all be cast
with the same mana. The score averages T1 through T7 and play/draw equally by
default, then subtracts the per-land dual/rainbow penalties. Mana shortage remains
in the draw distribution. Zero-weight cards still occupy deck slots.

This measures sustained availability with optimistic land selection. It ignores
sequencing, previously cast spells, tapped entry, conditional mana and Cavern.
Counts describe the actual spell package; weights describe importance. Deck size
is inferred from all land and spell counts. Only ordinary generic and WUBRG costs
are supported. Mana-base search and decklist import are not wired yet.

Run `python -m examples.sultai` for the sample Sultai cost profile and an
illustrative mana base. The [original decklist](resources/decks/evoke_elementals.txt)
is retained as sample input; all Sultai-specific choices live in the example.
See [calculation notes](ideas/knowledge/mana-opportunities.md) for the mathematics.

```sh
python -m unittest -v test_mana_opportunities
python -m doctest mana_opportunities.py
```

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
