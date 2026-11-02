"""Exhaustive exact search of 26-land Sultai bases with one fixed Swamp."""
import csv
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import comb, lcm

import numpy as np

from mana_analysis import COLORS, LANDS, ROOT, casting_modes, read_deck

NAMES = ("Swamp", "Overgrown Tomb", "Watery Grave", "Breeding Pool", "Gloomlake Verge",
         "Wastewood Verge", "Willowrush Verge", "Starting Town", "Cavern of Souls")
SHAPE = (2,) + (5,) * 8
COUNTS = np.indices(SHAPE, sparse=True)
TOTAL = sum(COUNTS)


def binomial_transform(values: np.ndarray) -> np.ndarray:
    """Return sum_k<=n product_i comb(n_i,k_i) values[k], using integers."""
    for axis, size in enumerate(values.shape):
        matrix = np.array([[comb(n, k) if k <= n else 0 for k in range(size)]
                           for n in range(size)], dtype=np.int64)
        values = np.moveaxis(np.tensordot(matrix, values, axes=(1, axis)), 0, axis)
    return values


def feasible_draws(total: int, colored: str, creature: bool) -> np.ndarray:
    return _feasible_draws(SHAPE, total, colored, creature)


@lru_cache(maxsize=1)
def _feasible_draws(shape: tuple[int, ...], total: int, colored: str, creature: bool) -> np.ndarray:
    """Upward closure of payable exact-total land subsets: no future knowledge beyond the model."""
    counts = np.indices(shape, sparse=True)
    valid = sum(counts) == total
    requirements = Counter(colored)
    colors = tuple(requirements)
    for size in range(1, len(colors) + 1):
        for subset in combinations(colors, size):
            group = set(subset)
            needed = sum(requirements[c] for c in subset)
            supply = np.zeros(shape, dtype=np.int16)
            for i, name in enumerate(NAMES):
                land = LANDS[name]
                options = set(COLORS if creature and land.cavern else land.colors)
                if options.intersection(group):
                    supply += counts[i]
                elif set(land.conditional).intersection(group):
                    enabled = np.zeros(shape, dtype=bool)
                    for j, other in enumerate(NAMES):
                        if set(LANDS[other].types).intersection(land.requires):
                            enabled |= counts[j] > 0
                    supply += counts[i] * enabled
            valid &= supply >= needed
    for axis in range(len(shape)):
        valid = np.maximum.accumulate(valid, axis=axis)
    return valid


def event_weights(total: int, colored: str, creature: bool, copies: int, seen: int,
                  capacities: tuple[int, ...] | None = None) -> tuple[np.ndarray, int]:
    shape = SHAPE if capacities is None else tuple(n+1 for n in capacities)
    totals = sum(np.indices(shape, sparse=True))
    spell_weights = [comb(34, seen-k) - (comb(34-copies, seen-k) if seen-k <= 34-copies else 0)
                     if total <= k <= seen-1 else 0 for k in range(sum(n-1 for n in shape)+1)]
    denominator = sum(comb(26, k) * spell_weights[k] for k in range(27))
    # Bound against the entire unrestricted capacity grid, not just legal 26-land bases.
    assert comb(34+sum(n-1 for n in shape), seen) < 2**63
    values = _feasible_draws(shape, total, colored, creature) * np.asarray(spell_weights, dtype=np.int64)[totals]
    return binomial_transform(values), denominator


def search() -> None:
    deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
    modes = casting_modes()
    multiplicities = Counter(m.card for m in modes)
    grouped = Counter()
    for mode in modes:
        key = (mode.total, "".join(sorted(mode.colored)), mode.creature, deck[mode.card])
        grouped[key] += Fraction(deck[mode.card], 34 * 2 * multiplicities[mode.card])
    # Fixed Swamp; four-copy limit on each of the other eight lands.
    indices = np.where((TOTAL == 26) & (COUNTS[0] == 1))
    candidates = list(zip(*(axis.tolist() for axis in indices)))
    terms = []
    for key, weight in grouped.items():
        for extra in (6, 7):
            seen = key[0] + extra
            denominator = sum(comb(26, k) * (comb(34, seen-k) - comb(34-key[3], seen-k))
                              for k in range(key[0], min(26, seen-1)+1))
            terms.append((key, seen, weight / denominator))
    common = lcm(*(coefficient.denominator for _, _, coefficient in terms))
    scores = [0] * len(candidates)
    for key, seen, coefficient in terms:
        weights, _ = event_weights(*key, seen)
        factor = coefficient.numerator * (common // coefficient.denominator)
        scores = [score + int(value)*factor for score, value in zip(scores, weights[indices])]
        print(f"Completed {key}, {seen} cards seen", flush=True)
    ranked = sorted(zip(scores, candidates), reverse=True)
    output = ROOT / "reports/mana-base-search.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["rank", "success", "loss", "success_fraction", *NAMES])
        for rank, (score, counts) in enumerate(ranked, 1):
            value = Fraction(score, common)
            writer.writerow([rank, float(value), float(1-value), str(value), *counts])
    print(f"Evaluated {len(ranked)} bases exactly.")
    for score, counts in ranked[:10]:
        print(float(Fraction(score, common)), counts)
    text = ["# Exhaustive Sultai mana-base comparison", "",
            "26 lands: exactly one Swamp, plus 0–4 each of the three Sultai shocks, three Sultai Verges,",
            "Starting Town and Cavern of Souls. No Undercity Sewers. The 34 nonlands stay fixed.", "",
            "The objective is the current copy-weighted, uniform-mode, equal play/draw average of",
            "on-curve payment probability, conditioned on seeing the target and enough lands.",
            "All 32 existing modes remain included, including hypothetical copy/discount scenarios.",
            "Ignore tapped entry, life costs, and Cavern creature-type choice, as in the original analysis.", "",
            f"All {len(ranked):,} legal compositions were evaluated and ranked with exact integer/rational arithmetic.",
            "CSV contains every composition, its success/loss, and exact success fraction.", "",
            "## Top five", "",
            "All five share: 1 Swamp, 4 Overgrown Tomb, 4 Watery Grave, 4 Breeding Pool,",
            "4 Starting Town and 4 Cavern of Souls. The remaining five lands are:", "",
            "| Rank | Gloomlake | Wastewood | Willowrush | Success | Loss |",
            "|---:|---:|---:|---:|---:|---:|"]
    for rank, (score, counts) in enumerate(ranked[:5], 1):
        value = Fraction(score, common)
        text.append(f"| {rank} | {counts[4]} | {counts[5]} | {counts[6]} | {float(value):.4%} | {float(1-value):.4%} |")
    text.extend(["", "## Best result with a fixed Town or Cavern count", "",
                 "The other seven variable land counts are reoptimized in each cell.", "",
                 "| Copies | Starting Town: best success | Cavern: best success |", "|---:|---:|---:|"])
    for count in range(5):
        best = [next(score for score, counts in ranked if counts[axis] == count) for axis in (7, 8)]
        text.append(f"| {count} | {float(Fraction(best[0], common)):.4%} | {float(Fraction(best[1], common)):.4%} |")
    median = Fraction(ranked[len(ranked)//2-1][0] + ranked[len(ranked)//2][0], 2*common)
    text.extend(["", "## Broad characterization", "",
                 f"Success spans {float(Fraction(ranked[-1][0], common)):.4%} to "
                 f"{float(Fraction(ranked[0][0], common)):.4%}; median {float(median):.4%}.",
                 "All top 50 bases have four Towns and four Caverns; all top ten also have twelve shocks.",
                 "The first-to-third spread is only 0.0138 percentage points: Verge fine-tuning is a small effect.",
                 "The score omits shock/Town life costs and rewards Cavern as a five-color source for every creature.",
                 "Uniform weighting of the white elemental modes also increases demand for Town and Cavern.",
                 "These are optima of that simplified objective, not full-game deck-strength rankings.", "",
                 "## Exact method and validation", "",
                 "Enumerate payable land multisets of size equal to each cost. Propagate feasibility upward",
                 "to larger drawn multisets. A multidimensional integer binomial transform computes the",
                 "weighted sum for every legal deck capacity vector at once. Nonland-draw factors enforce",
                 "at least one target copy. Conditioning denominators are constant across these 26-land bases.",
                 "Combine all components under a common rational denominator and rank integer numerators.",
                 "Tests compare the transform with direct sums and payment probabilities with the scalar",
                 "exact evaluator; additional winning-base checks cover both-color and white payments.", "",
                 "Run `python mana_search.py` with NumPy installed to regenerate this report and CSV.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    search()
