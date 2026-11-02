# Exhaustive Sultai mana-base comparison

26 lands: exactly one Swamp, plus 0–4 each of the three Sultai shocks, three Sultai Verges,
Starting Town and Cavern of Souls. No Undercity Sewers. The 34 nonlands stay fixed.

The objective is the current copy-weighted, uniform-mode, equal play/draw average of
on-curve payment probability, conditioned on seeing the target and enough lands.
All 32 existing modes remain included, including hypothetical copy/discount scenarios.
Ignore tapped entry, life costs, and Cavern creature-type choice, as in the original analysis.

All 3,144 legal compositions were evaluated and ranked with exact integer/rational arithmetic.
CSV contains every composition, its success/loss, and exact success fraction.

## Top five

All five share: 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 4 Breeding Pool,
4 Starting Town and 4 Cavern of Souls. The remaining five lands are:

| Rank | Gloomlake | Wastewood | Willowrush | Success | Loss |
|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 1 | 1 | 90.1966% | 9.8034% |
| 2 | 3 | 0 | 2 | 90.1891% | 9.8109% |
| 3 | 4 | 0 | 1 | 90.1828% | 9.8172% |
| 4 | 2 | 1 | 2 | 90.1490% | 9.8510% |
| 5 | 4 | 1 | 0 | 90.1365% | 9.8635% |

## Best result with a fixed Town or Cavern count

The other seven variable land counts are reoptimized in each cell.

| Copies | Starting Town: best success | Cavern: best success |
|---:|---:|---:|
| 0 | 83.8015% | 86.2051% |
| 1 | 85.5643% | 87.3627% |
| 2 | 87.2487% | 88.4425% |
| 3 | 88.7917% | 89.3907% |
| 4 | 90.1966% | 90.1966% |

## Broad characterization

Success spans 79.5551% to 90.1966%; median 86.0616%.
All top 50 bases have four Towns and four Caverns; all top ten also have twelve shocks.
The first-to-third spread is only 0.0138 percentage points: Verge fine-tuning is a small effect.
The score omits shock/Town life costs and rewards Cavern as a five-color source for every creature.
Uniform weighting of the white elemental modes also increases demand for Town and Cavern.
These are optima of that simplified objective, not full-game deck-strength rankings.

## Exact method and validation

Enumerate payable land multisets of size equal to each cost. Propagate feasibility upward
to larger drawn multisets. A multidimensional integer binomial transform computes the
weighted sum for every legal deck capacity vector at once. Nonland-draw factors enforce
at least one target copy. Conditioning denominators are constant across these 26-land bases.
Combine all components under a common rational denominator and rank integer numerators.
Tests compare the transform with direct sums and payment probabilities with the scalar
exact evaluator; additional winning-base checks cover both-color and white payments.

Run `python mana_search.py` with NumPy installed to regenerate this report and CSV.
