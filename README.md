# MTG hand experiments

## Interactive mana explorer

Install the notebook extras with `uv sync --extra notebook`, then run `uv run jupyter lab`
and open [mana_explorer.ipynb](mana_explorer.ipynb). Run its setup cell, choose spell copies,
weights and penalty, then press **Run analysis**. The land count is inferred from 60 cards.
The display marks results stale when inputs change; a full run can take several minutes.
The search is exhaustive only within the bounded land pool described in the notebook.

## Full optimum and swap report

Run `python mana_report.py --config mana-report.json` to regenerate the
[complete mana report](reports/mana-report.md): optimal 26-land base, 34 nonlands, per-card
lower/higher-importance crossing swaps, and separate play/draw T1–T6 coverage tables.
The supplied configuration explicitly replaces one Awaken with one Bitter Triumph and fixes lambda=0.0032.
The source deck file stays unchanged. Every input, candidate and suggested resulting deck must contain 60 cards.

Each suggestion records the exact first crossing, concrete OUT/IN counts, the target card's probability
change and the fitness cost at the original weights. Scores tie at the crossing; the new base wins just beyond it.
The report also compares both spell packages and isolates the gain from adjusting the lands under the revised package.
Search is exhaustive in the established bounded 59,109-base pool, not unrestricted-basics optimization.

JSON retains exact fractions; CSV exports the two directions per card, and `.deck.txt` exports the optimal full deck.
Configure `deck`, physical nonland `changes`, positive per-card `weights`, `penalty`, and `output` in JSON.
Paths are relative to the config file. CLI options override defaults; explicit `--changes` and `--weights` take JSON objects.
Omitting the configuration applies no physical spell-count changes.

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
The same command writes an [8–12 shock penalty sweep](reports/shock-penalty-sweep.md), including
exact optimality intervals, example coefficients and each winning composition.

`python mana_basic_search.py` tests adding basics around those optima and evaluates all 59,109 bases
with up to two Swamps, one Island and one Forest. See [basic-land sensitivity](reports/basic-land-sensitivity.md).
This is a bounded neighborhood, not an exhaustive search with unrestricted basics.
It also writes the [basic-land penalty frontier](reports/basic-land-penalty-frontier.md) and
the [first shock-return transition](reports/basic-shock-transition.md) when reducing lambda from 0.004.

`python mana_card_weight_search.py` increases Awaken the Honored Dead's relative importance at
lambda=0.0032 until the optimal base changes. Use `--weight 1.10` to set the multiplier explicitly.
`--config weights.json` accepts `weight`, `penalty` and `output` defaults; CLI options take precedence.
Weights multiply physical copy counts and the weighted average is renormalized; mode/play-draw
weights stay uniform. See [Awaken weight sensitivity](reports/awaken-weight-search.md).

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
