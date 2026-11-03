"""Exact cross-base binomial transforms for bounded mana pools.

NumPy is imported only by this backend. Integer limbs keep every transform
within int64, even when averaging turns creates large rational numerators.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping
from fractions import Fraction
from itertools import combinations
from math import comb, lcm

import numpy as np

from mana_opportunities import ManaSource, VERGE_RULES

def binomial_transform(values: np.ndarray, max_drawn: int | None = None) -> np.ndarray:
    """Sum product(comb(capacity, drawn)) * values[drawn] for all capacities."""
    for axis, size in enumerate(values.shape):
        matrix = np.array([[comb(n, k) if k <= n and (max_drawn is None or k <= max_drawn) else 0
                            for k in range(size)]
                           for n in range(size)], dtype=np.int64)
        values = np.moveaxis(np.tensordot(matrix, values, axes=(1, axis)), 0, axis)
    return values


def component_columns(bounds: Mapping[ManaSource, tuple[int, int]], land_count: int,
                      copies: Mapping[str, Fraction], candidates: tuple[tuple[int, ...], ...], *,
                      nonlands: int, turns: int, position: str, opening_hand_size: int,
                      progress: Callable[[Iterable[str]], Iterable[str]] | None = None
                      ) -> Iterator[tuple[str, tuple[Fraction, ...]]]:
    """Return exact mean mode-copy opportunities per cost for all candidates."""
    sources = tuple(bounds)
    capacities = tuple(hi for _, hi in bounds.values())
    shape = tuple(n + 1 for n in capacities)
    counts = tuple(np.indices(shape, sparse=True))
    totals = sum(counts, np.zeros(shape, dtype=np.int64))
    indices = tuple(np.asarray([c[i] for c in candidates], dtype=np.intp) for i in range(len(sources)))
    deck_size = land_count + nonlands
    sides = ("play", "draw") if position == "both" else (position,)
    seen_by_turn = [(turn, min(deck_size, opening_hand_size + turn - (side == "play")))
                    for turn in range(1, turns + 1) for side in sides]
    max_drawn = min(land_count, max(seen for _, seen in seen_by_turn) - 1)
    # Every partial transform is bounded by this many land subsets times the
    # largest input limb. All entries and binomial coefficients are nonnegative.
    draw_mass = sum(comb(sum(capacities), k) for k in range(max(0, max_drawn + 1)))
    limb_bits = ((2**63 - 1) // max(1, draw_mass) + 1).bit_length() - 1
    if limb_bits < 1:
        raise OverflowError("Batch land subset counts exceed int64; use backend='scalar'")
    limb_mask = (1 << limb_bits) - 1
    enabled = {}
    for source in sources:
        if source.kind == "verge" and source.colors not in enabled:
            rule = VERGE_RULES[source.colors]
            flag = np.zeros(shape, dtype=bool)
            for other, drawn in zip(sources, counts):
                if set(other.types).intersection(rule.requires):
                    flag |= drawn > 0
            enabled[source.colors] = flag

    costs = progress(copies) if progress is not None else copies
    for cost in costs:
        generic = int(cost.rstrip("WUBRG") or 0)
        required = Counter(c for c in cost if c in "WUBRG")
        total = generic + sum(required.values())
        if not copies[cost] or total > turns or not nonlands:
            yield cost, (Fraction(),) * len(candidates)
            continue
        # Average the spell-draw factors first, so only a few limb transforms
        # are needed per cost, rather than one transform per turn/position.
        factors = [sum((Fraction(comb(nonlands - 1, seen - k - 1), comb(deck_size, seen))
                        for turn, seen in seen_by_turn
                        if turn >= total and 0 <= seen - k - 1 < nonlands), Fraction())
                   / len(seen_by_turn) for k in range(max_drawn + 1)]
        denominator = lcm(*(f.denominator for f in factors))
        coefficients = [f.numerator * (denominator // f.denominator) for f in factors]
        valid = (totals >= total) & (totals <= max_drawn)
        colors = tuple(required)
        for size in range(1, len(colors) + 1):
            for subset in combinations(colors, size):
                group = set(subset)
                supply = np.zeros(shape, dtype=np.int64)
                for source, drawn in zip(sources, counts):
                    if group.intersection(source.primary_colors):
                        supply += drawn
                    elif source.kind == "verge" and VERGE_RULES[source.colors].secondary in group:
                        supply += drawn * enabled[source.colors]
                valid &= supply >= sum(required[c] for c in subset)
        numerators = [0] * len(candidates)
        for shift in range(0, max(coefficients, default=0).bit_length(), limb_bits):
            digits = [(value >> shift) & limb_mask for value in coefficients]
            if not any(digits):
                continue
            lookup = np.array(digits + [0] * (sum(capacities) + 1 - len(digits)), dtype=np.int64)
            transformed = binomial_transform(valid * lookup[totals], max_drawn=max_drawn)
            selected = np.atleast_1d(transformed[indices])
            numerators = [a + (int(b) << shift) for a, b in zip(numerators, selected)]
        yield cost, tuple(copies[cost] * Fraction(n, denominator) for n in numerators)
