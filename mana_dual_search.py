"""Exact exhaustive ranking of 26-land bases drawn from three unlimited Sultai duals."""
import csv
from collections import Counter
from fractions import Fraction
from itertools import combinations
from math import comb, lcm

import numpy as np

from hands import compositions
from mana_analysis import ROOT, casting_modes, read_deck

NAMES = ("U/B dual", "B/G dual", "U/G dual")
OPTIONS = ("UB", "BG", "UG")
BASES = tuple(compositions((26, 26, 26), 26))
DRAWS = np.array([counts for k in range(16) for counts in compositions((15, 15, 15), k)])
TOTAL = DRAWS.sum(axis=1)
CHOOSE = np.array([[comb(n, k) if k <= n else 0 for k in range(16)] for n in range(27)], dtype=np.int64)
DRAW_WEIGHTS = np.prod([CHOOSE[np.array(BASES)[:, i, None], DRAWS[None, :, i]] for i in range(3)], axis=0)


def event_weights(total: int, colored: str, copies: int, seen: int) -> tuple[np.ndarray, int]:
    """Successful integer draw counts for each of the 378 bases; common conditional denominator."""
    valid = TOTAL >= total
    required = Counter(colored)
    for size in range(1, len(required)+1):
        for group in combinations(required, size):
            sources = [i for i, options in enumerate(OPTIONS) if set(options).intersection(group)]
            valid &= DRAWS[:, sources].sum(axis=1) >= sum(required[c] for c in group)
    factors = np.array([comb(34, seen-k) - comb(34-copies, seen-k)
                        if total <= k < seen else 0 for k in range(16)], dtype=np.int64)
    denominator = sum(comb(26, k)*int(factors[k]) for k in range(16))
    assert comb(60, seen) < 2**63
    return DRAW_WEIGHTS @ (valid*factors[TOTAL]), denominator


def search() -> None:
    deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
    modes = casting_modes()
    multiplicities = Counter(m.card for m in modes)
    grouped = Counter()
    for mode in modes:
        key = (mode.total, "".join(sorted(mode.colored)), deck[mode.card])
        grouped[key] += Fraction(deck[mode.card], 34*2*multiplicities[mode.card])
    terms = []
    for key, weight in grouped.items():
        for extra in (6, 7):
            numerators, denominator = event_weights(*key, key[0]+extra)
            terms.append((numerators, weight/denominator))
    common = lcm(*(coefficient.denominator for _, coefficient in terms))
    scores = [0]*len(BASES)
    for numerators, coefficient in terms:
        factor = coefficient.numerator*(common//coefficient.denominator)
        scores = [score+int(n)*factor for score, n in zip(scores, numerators)]
    ranked = sorted(zip(scores, BASES), reverse=True)
    output = ROOT / "reports/idealized-dual-search.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["rank", *NAMES, "success", "loss", "success_fraction"])
        for rank, (score, counts) in enumerate(ranked, 1):
            value = Fraction(score, common)
            writer.writerow([rank, *counts, float(value), float(1-value), str(value)])
    text = ["# Idealized Sultai dual search", "",
            "All 26 lands are unconditional U/B, B/G or U/G duals, with unlimited copies and no fixed Swamp.",
            "The same 34 nonlands, 32 modes, uniform mode weights, equal play/draw weights and sufficient-land",
            "conditioning remain in place. Life and tapped entry are ignored. No source produces white.", "",
            "All 378 integer distributions were evaluated and ranked using exact integer/rational arithmetic.", "",
            "| Rank | U/B | B/G | U/G | Success | Loss |", "|---:|---:|---:|---:|---:|---:|"]
    for rank, (score, counts) in enumerate(ranked[:10], 1):
        value = Fraction(score, common)
        text.append(f"| {rank} | {counts[0]} | {counts[1]} | {counts[2]} | {float(value):.6%} | {float(1-value):.6%} |")
    impossible = Fraction(4, 34)*Fraction(3, 5) + Fraction(4, 34)*Fraction(1, 8)
    text.extend(["", f"White requirements alone impose a loss floor of {float(impossible):.6%}:",
                 "three of Emptiness's five modes and one of Spider-Man's eight modes are impossible.",
                 "Consequently the theoretical success ceiling is 91.470588%, even with perfect U/B/G access.", "",
                 "The CSV includes all distributions and exact success fractions.",
                 "Run `python mana_dual_search.py` with NumPy installed to regenerate.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")
    for score, counts in ranked[:10]:
        print(counts, float(Fraction(score, common)), flush=True)
    best = ranked[0][1]
    index = BASES.index(best)
    print("BEST CARD SCORES")
    for card in multiplicities:
        probabilities = []
        for mode in (m for m in modes if m.card == card):
            for extra in (6, 7):
                numerator, denominator = event_weights(mode.total, mode.colored, deck[card], mode.total+extra)
                probabilities.append(Fraction(int(numerator[index]), denominator))
        print(card, float(sum(probabilities, Fraction())/len(probabilities)))


if __name__ == "__main__":
    search()
