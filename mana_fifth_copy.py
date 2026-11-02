"""Exact fifth-copy experiments at lambda=0.004, with a fixed Swamp and 26 lands."""
import csv
from collections import Counter
from fractions import Fraction
from math import lcm

import numpy as np

from mana_analysis import ROOT, casting_modes, read_deck
from mana_search import NAMES, event_weights

CAPACITIES = (1, 5, 5, 4, 4, 4, 4, 5, 5)
BASELINE = (1, 4, 4, 2, 3, 1, 3, 4, 4)
PENALTY = Fraction("0.004")


def search() -> None:
    shape = tuple(n+1 for n in CAPACITIES)
    coordinates = np.indices(shape, sparse=True)
    indices = np.where((sum(coordinates) == 26) & (coordinates[0] == 1))
    bases = list(zip(*(axis.tolist() for axis in indices)))
    deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
    modes = casting_modes()
    multiplicities = Counter(m.card for m in modes)
    grouped = Counter()
    for mode in modes:
        key = (mode.total, "".join(sorted(mode.colored)), mode.creature, deck[mode.card])
        grouped[key] += Fraction(deck[mode.card], 34*2*multiplicities[mode.card])
    terms = []
    for key, weight in grouped.items():
        for extra in (6, 7):
            weights, denominator = event_weights(*key, key[0]+extra, capacities=CAPACITIES)
            terms.append((weights[indices], weight/denominator))
    common = lcm(PENALTY.denominator, *(coefficient.denominator for _, coefficient in terms))
    scores = [0]*len(bases)
    for weights, coefficient in terms:
        factor = coefficient.numerator*(common//coefficient.denominator)
        scores = [score+int(n)*factor for score, n in zip(scores, weights)]
    successes = dict(zip(bases, scores))
    def loss(base: tuple[int, ...]) -> int:
        penalized = sum(base[i] for i in (1, 2, 3, 7))
        return common-successes[base]+PENALTY.numerator*(common//PENALTY.denominator)*penalized
    def describe(base: tuple[int, ...]) -> str:
        delta = ", ".join(f"{base[i]-BASELINE[i]:+d} {name}" for i, name in enumerate(NAMES)
                          if base[i] != BASELINE[i]) or "unchanged"
        return (f"{delta}; raw success {float(Fraction(successes[base], common)):.6%}; "
                f"regularized loss {float(Fraction(loss(base), common)):.6%}; "
                f"improvement {float(Fraction(loss(BASELINE)-loss(base), common))*100:.6f} pp")
    text = ["# Fifth-copy experiments", "", "26 lands, fixed Swamp, lambda=0.004 per shock or Town.",
            "Other cards retain four-copy limits. Results use exact fractions and exhaustive comparison.",
            f"Evaluated {len(bases):,} bases with up to five Tomb, Grave, Town and Cavern.", "",
            "Baseline: " + describe(BASELINE), ""]
    for axis in (7, 1, 2, 8):
        eligible = [base for base in bases if all(base[i] <= 4 for i in (1, 2, 7, 8) if i != axis)]
        best = min(eligible, key=loss)
        local = []
        for cut in range(1, len(NAMES)):
            if cut != axis and BASELINE[cut]:
                base = list(BASELINE)
                base[axis] += 1
                base[cut] -= 1
                local.append(tuple(base))
        best_local = min(local, key=loss)
        text.extend([f"## Fifth {NAMES[axis]}", "", "Best one-card swap: " + describe(best_local), "",
                     "Best after reoptimizing all other counts: " + describe(best), ""])
    best = min(bases, key=loss)
    text.extend(["## All four fifth copies allowed together", "", describe(best), "",
                 "Winning composition: " + ", ".join(f"{n} {name}" for name, n in zip(NAMES, best)), ""])
    output = ROOT / "reports/fifth-copy-search.md"
    output.write_text("\n".join(text), encoding="utf-8")
    print("\n".join(text), flush=True)
    with output.with_suffix(".csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["rank", *NAMES, "success_fraction", "regularized_loss_fraction"])
        for rank, base in enumerate(sorted(bases, key=loss), 1):
            writer.writerow([rank, *base, str(Fraction(successes[base], common)), str(Fraction(loss(base), common))])


if __name__ == "__main__":
    search()
