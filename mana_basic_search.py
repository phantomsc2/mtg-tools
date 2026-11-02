"""Exact marginal tests for basics around the direct-metric penalty optima."""
import csv
from collections import Counter
from fractions import Fraction
from math import lcm

import numpy as np

from mana_analysis import LANDS, ROOT, casting_modes, read_deck
from mana_search import NAMES as ORIGINAL_NAMES, event_weights
from mana_regularization import frontier
from mana_fitness import mode_weights

NAMES = ORIGINAL_NAMES + ("Island", "Forest")
# First neighborhood: one additional copy of each basic; nonbasics keep their caps.
CAPACITIES = (2,)+(4,)*8+(1, 1)
PENALTIES = tuple(map(Fraction, ("0", "0.003", "0.004", "0.005", "0.008")))


def write_frontier(successes: dict[tuple[int, ...], int], common: int) -> None:
    best = {}
    for base, success in successes.items():
        count = sum(base[i] for i in (1, 2, 3, 7))
        if count not in best or success > best[count][0]:
            best[count] = (success, base)
    intervals = frontier({count: Fraction(pair[0], common) for count, pair in best.items()})
    output = ROOT / "reports/basic-land-penalty-frontier.csv"
    text = ["# Basic-land penalty frontier", "",
            "Exact optima within the 59,109-base neighborhood: 26 lands, at least one Swamp,",
            "up to two Swamps, one Island and one Forest, four-copy nonbasic limits. No Passage.",
            "Loss = color failure + lambda * (shock count + Town count). Endpoints can tie.", "",
            "| Shocks | Towns | Color success | Lambda from | Lambda to | Composition |",
            "|---:|---:|---:|---:|---:|---|"]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["shocks", "penalized_count", "success_fraction", "lambda_from_fraction",
                         "lambda_to_fraction", *NAMES])
        for count, lower, upper in intervals:
            success, base = best[count]
            value = Fraction(success, common)
            shocks = sum(base[i] for i in (1, 2, 3))
            writer.writerow([shocks, count, str(value), str(lower), str(upper) if upper is not None else "",
                             *base])
            end = f"{float(upper):.10f}" if upper is not None else "unbounded"
            composition = ", ".join(f"{n} {name}" for n, name in zip(base, NAMES) if n)
            text.append(f"| {shocks} | {base[7]} | {float(value):.6%} | {float(lower):.10f} | {end} | "
                        f"{composition} |")
            print("FRONTIER", shocks, "lambda", float(lower), end, base, float(value), flush=True)
    output.with_suffix(".md").write_text("\n".join(text)+"\n", encoding="utf-8")
    # Record the first transition when lowering lambda from the three-basic .004 optimum.
    reference = Fraction("0.004")
    current = next((n, low, high) for n, low, high in intervals
                   if low <= reference and (high is None or reference < high))
    next_interval = next((item for item in intervals if item[2] == current[1]), None)
    if next_interval is not None:
        count, lower, upper = next_interval
        old_score, old_base = best[current[0]]
        new_score, new_base = best[count]
        coefficient = Fraction("0.0032")
        assert lower < coefficient < upper
        threshold = Fraction(new_score-old_score, common*(count-current[0]))
        assert threshold == current[1]
        def objective(pair):
            return Fraction(pair[0], common)-coefficient*sum(pair[1][i] for i in (1, 2, 3, 7))
        assert objective((new_score, new_base)) == max(objective(pair) for pair in best.values())
        transition = ["# Returning one shock to the three-basic base", "",
                      "Same bounded 59,109-base pool as the basic-land sensitivity analysis; no Passage.",
                      "Start at lambda=0.004: 2 Swamp, 1 Island and nine shocks.", "",
                      f"The first transition on lowering lambda occurs at {float(threshold):.12f}",
                      f"(exact fraction {threshold}). At the threshold the two bases tie.",
                      "Below it, replace Island with Breeding Pool. Starting Town and Cavern remain at four.", "",
                      f"Use lambda={coefficient}, a {float(coefficient)*100:.2f} percentage-point penalty "
                      "per shock or Town.",
                      f"This ten-shock optimum is selected between {float(lower):.12f} and {float(upper):.12f};",
                      "endpoints tie with adjacent frontier bases.", "", "| Land | Before | After |",
                      "|---|---:|---:|"]
        transition.extend(f"| {name} | {old} | {new} |" for name, old, new in zip(NAMES, old_base, new_base)
                          if old or new)
        transition.extend(["", f"Raw success: {float(Fraction(old_score, common)):.6%} → "
                           f"{float(Fraction(new_score, common)):.6%}.",
                           f"At lambda=.0032, new regularized loss: "
                           f"{float(1-Fraction(new_score, common)+coefficient*count):.6%}.", ""])
        (ROOT / "reports/basic-shock-transition.md").write_text("\n".join(transition), encoding="utf-8")


def evaluate_pool(deck: Counter | None = None, component_cache: dict | None = None, progress=None) -> tuple[list, dict, int, dict]:
    deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt") if deck is None else deck
    if any(type(n) is not int or n < 0 for n in deck.values()):
        raise ValueError("Deck counts must be nonnegative integers")
    if sum(deck.values()) != 60:
        raise ValueError("Pool evaluation requires exactly 60 cards")
    land_count = sum(deck[n] for n in deck if n in LANDS)
    deck = Counter({name: n for name, n in deck.items() if n})
    shape = tuple(n+1 for n in CAPACITIES)
    counts = np.indices(shape, sparse=True)
    indices = np.where((sum(counts) == land_count) & (counts[0] >= 1))
    bases = list(zip(*(axis.tolist() for axis in indices)))
    if not bases:
        raise ValueError(f"No candidate land bases for {land_count} lands in the bounded pool")
    modes = [mode for mode in casting_modes() if deck[mode.card]]
    grouped = Counter()
    for mode, weight in mode_weights(deck, modes):
        grouped[(mode.total, "".join(sorted(mode.colored)), mode.creature, deck[mode.card])] += weight
    terms = []
    components = {}
    for position, (key, weight) in enumerate(grouped.items(), 1):
        cache_key = (land_count, key)
        if component_cache is not None and cache_key in component_cache:
            components[key] = component_cache[cache_key]
        else:
            components[key] = []
            for extra in (6, 7):
                values, denominator = event_weights(*key, key[0]+extra, capacities=CAPACITIES, names=NAMES, land_count=land_count)
                components[key].append((values[indices], denominator))
            if component_cache is not None:
                component_cache[cache_key] = components[key]
        for numerators, denominator in components[key]:
            terms.append((numerators, weight/denominator))
        if progress:
            progress(position, len(grouped), f"Evaluated requirement {key}")
        else:
            print(f"Completed {key}", flush=True)
    common = lcm(*(c.denominator for _, c in terms), *(c.denominator for c in PENALTIES))
    scores = [0]*len(bases)
    for values, coefficient in terms:
        factor = coefficient.numerator*(common//coefficient.denominator)
        scores = [score+int(n)*factor for score, n in zip(scores, values)]
    successes = dict(zip(bases, scores))
    return bases, successes, common, components


def evaluate_neighborhood() -> None:
    bases, successes, common, _ = evaluate_pool()
    write_frontier(successes, common)
    with (ROOT / "reports/shock-penalty-sweep.csv").open(encoding="utf-8") as stream:
        originals = list(csv.DictReader(stream))
    text = ["# Basic-land sensitivity", "",
            "Same direct metric, land-life penalty, 26 lands and at least one Swamp.",
            "This is NOT an unrestricted-basic exhaustive search: the evaluated neighborhood allows",
            "up to two Swamps, one Island and one Forest, with four-copy nonbasic limits.",
            f"Evaluated {len(bases):,} compositions exactly, plus every one-card basic swap "
            "from each original optimum.", ""]
    for penalty, original in zip(PENALTIES, originals):
        base = tuple(int(original[n]) for n in ORIGINAL_NAMES)+(0, 0)
        def score(b):
            penalized = sum(b[i] for i in (1, 2, 3, 7))
            return successes[b]-penalty.numerator*(common//penalty.denominator)*penalized
        assert Fraction(successes[base], common) == Fraction(original["success_fraction"])
        baseline = score(base)
        text.extend([f"## Lambda {float(penalty):g}", "",
                     "| Add | Best cut | Improvement in penalized score (pp) |", "|---|---|---:|"])
        for axis in (0, 9, 10):
            swaps = []
            for cut in range(1, len(NAMES)):
                if cut != axis and base[cut]:
                    changed = list(base)
                    changed[axis] += 1
                    changed[cut] -= 1
                    swaps.append((tuple(changed), NAMES[cut]))
            winner, cut = max(swaps, key=lambda pair: score(pair[0]))
            text.append(f"| {NAMES[axis]} | {cut} | {float(Fraction(score(winner)-baseline, common))*100:+.6f} |")
        best = max(bases, key=score)
        text.extend(["", "Best within evaluated neighborhood: " + ", ".join(
            f"{n} {name}" for name, n in zip(NAMES, best) if n),
            f"Raw success {float(Fraction(successes[best], common)):.6%}; improvement "
            f"{float(Fraction(score(best)-baseline, common))*100:+.6f} pp.", ""])
        print(float(penalty), best, float(Fraction(score(best)-baseline, common))*100, flush=True)
    (ROOT / "reports/basic-land-sensitivity.md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    evaluate_neighborhood()
