# MTG hand experiments

## Sultai mana-base analysis

Run `python mana_analysis.py` for the main deck in `resources/decks/evoke_elementals.txt`.
The [full table](reports/sultai-mana.md) reports every nonland and agreed casting mode on the play/draw;
the [CSV](reports/sultai-mana.csv) retains exact fractions and integer event weights.
See [assumptions and mathematics](ideas/knowledge/mana-analysis.md) for the conditioning model,
conditional lands, Spider-Man copying Elementals, and hypothetical Sunderflock discount scenarios.
This command needs only the standard library.

Run `python mana_search.py` (requires NumPy) for an exhaustive comparison of all 26-land bases
with one fixed Swamp and up to four of each Sultai shock, Sultai Verge, Starting Town and Cavern.
See the [search results](reports/mana-base-search.md) and [complete exact ranking](reports/mana-base-search.csv).

`python mana_dual_search.py` evaluates all 378 distributions of 26 unlimited U/B, B/G and U/G duals.
See the [idealized dual results](reports/idealized-dual-search.md).

`python mana_regularization.py --penalty 0.004` ranks the actual pool after adding a constant
loss penalty per shockland or Starting Town. See the [regularized results](reports/regularized-mana-search.md).

`python mana_fifth_copy.py` tests fifth Town, Tomb, Grave and Cavern copies independently and together,
at the same regularization weight. See the [fifth-copy results](reports/fifth-copy-search.md).

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
tapped lands, sideboards, and playouts. The original scripts are retained as historical experiments.
