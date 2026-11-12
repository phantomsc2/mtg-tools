"""Exact cross-base binomial transforms for bounded mana pools.

NumPy is imported only by this backend. Integer limbs keep every transform
within int64, even when averaging turns creates large rational numerators.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from fractions import Fraction
from math import comb, lcm

import numpy as np

from mtg_tools.mana_lands import ManaSource
from mtg_tools.mana_model import CompiledManaModel
from mtg_tools.mana_payment import Distribution, PaymentScenario, payment_scenarios, probability_counter, requirements


def binomial_transform(values: np.ndarray, max_drawn: int | None = None) -> np.ndarray:
    """Sum product(comb(capacity, drawn)) * values[drawn] for all capacities."""
    for axis, size in enumerate(values.shape):
        matrix = np.array([[comb(n, k) if k <= n and (max_drawn is None or k <= max_drawn) else 0
                            for k in range(size)]
                           for n in range(size)], dtype=np.int64)
        values = np.moveaxis(np.tensordot(matrix, values, axes=(1, axis)), 0, axis)
    return values


def _payment_keys(scenario: PaymentScenario, counts: tuple[np.ndarray, ...], totals: np.ndarray,
                  caps: tuple[int, ...], max_drawn: int, groups: dict[Distribution, np.ndarray]
                  ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, tuple[int, ...]]:
    """Deduplicate draws by residual constraints, independent of probability values."""
    valid = (totals >= caps[0]) & (totals <= max_drawn)
    if any(scenario.type_masks):
        observed = np.zeros(totals.shape, dtype=np.uint8)
        for mask, drawn in zip(scenario.type_masks, counts):
            if mask:
                observed |= np.asarray((drawn > 0) * mask, dtype=np.uint8)
        valid &= np.isin(observed, scenario.contexts)
    covered = [np.zeros(totals.shape, dtype=np.int64) for _ in caps]
    possible = [np.zeros(totals.shape, dtype=np.int64) for _ in caps]
    for distribution, drawn in zip(scenario.distributions, counts):
        for j in range(len(caps)):
            possible[j] += drawn * max(supply[j] for supply, _ in distribution)
        if len(distribution) == 1:
            for have, n in zip(covered, distribution[0][0]):
                have += drawn * n
    for cap, supply in zip(caps, possible):
        valid &= supply >= cap
    if not groups or not valid.any():
        return valid, None, None, ()
    needs = [np.maximum(0, cap - have) for cap, have in zip(caps, covered)]
    # Identical random increments make several constraints one maximum deficit.
    constraints = {}
    for j, need in enumerate(needs):
        signature = tuple(tuple(supply[j] for supply, _ in dist) for dist in groups)
        if signature in constraints:
            axis, previous = constraints[signature]
            constraints[signature] = axis, np.maximum(previous, need)
        else:
            constraints[signature] = j, need
    axes, needs = zip(*constraints.values())
    arrays = [totals, *needs, *groups.values()]
    keys, inverse = np.unique(np.stack([np.broadcast_to(n, totals.shape)[valid] for n in arrays], axis=1),
                              axis=0, return_inverse=True)
    return valid, keys, inverse, axes


def _opportunity_grid(counts: tuple[np.ndarray, ...], totals: np.ndarray,
                      scenarios: dict[PaymentScenario, list[Fraction]], caps: tuple[int, ...],
                      max_drawn: int) -> tuple[np.ndarray, int]:
    """Exact joint-payment weights, reused by residual requirements and source counts."""
    scales = {scenario: lcm(*(p.denominator for dist in scenario.distributions for _, p in dist))
              for scenario in scenarios}
    denominator = lcm(*(factor.denominator * scales[scenario]**max_drawn
                        for scenario, factors in scenarios.items() for factor in factors))
    values = np.zeros(totals.shape, dtype=object)
    layouts = {}
    for scenario, factors in scenarios.items():
        groups = {}
        for distribution, drawn in zip(scenario.distributions, counts):
            if len(distribution) > 1:
                groups[distribution] = groups.get(distribution, 0) + drawn
        indices = {dist: i for i, dist in enumerate(groups)}
        layout = (scenario.type_masks, scenario.contexts,
                  tuple((0, dist[0][0]) if len(dist) == 1 else (1, indices[dist])
                        for dist in scenario.distributions),
                  tuple(tuple(supply for supply, _ in dist) for dist in groups))
        if layout not in layouts:
            layouts[layout] = _payment_keys(scenario, counts, totals, caps, max_drawn, groups)
        valid, keys, inverse, axes = layouts[layout]
        if not valid.any():
            continue
        if not groups:
            coefficients = np.array([f.numerator * (denominator // f.denominator) for f in factors], dtype=object)
            values[valid] += coefficients[totals[valid]]
            continue
        distributions = tuple(tuple((tuple(supply[j] for j in axes), p) for supply, p in dist) for dist in groups)
        mass, scale = probability_counter(distributions)
        weights = []
        for key in keys:
            k, *rest = map(int, key)
            required, drawn = tuple(rest[:len(axes)]), tuple(rest[len(axes):])
            factor = factors[k]
            weights.append(mass(drawn, required) * factor.numerator
                           * (denominator // (factor.denominator * scale**sum(drawn))))
        values[valid] += np.asarray(weights, dtype=object)[inverse]
        mass.cache_clear()
    return values, denominator


def component_columns(bounds: Mapping[ManaSource, tuple[int, int]], land_count: int,
                      copies: Mapping[str, Fraction], candidates: tuple[tuple[int, ...], ...], *,
                      nonlands: int, turns: int, position: str, opening_hand_size: int,
                      model: CompiledManaModel, turn_weights: tuple[Fraction, ...] | None = None,
                      progress: Callable[[Iterable[str]], Iterable[str]] | None = None
                      ) -> Iterator[tuple[str, tuple[Fraction, ...]]]:
    """Return exact mean mode-copy opportunities per cost for all candidates."""
    if turn_weights is None:
        turn_weights = (Fraction(1, turns),) * turns
    if len(turn_weights) != turns or sum(turn_weights) != 1 or any(w < 0 for w in turn_weights):
        raise ValueError("Turn weights must be normalized and match the horizon")
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
    max_drawn = min(land_count, max(0, max(seen for _, seen in seen_by_turn) - 1))
    # Every partial transform is bounded by this many land subsets times the
    # largest input limb. All entries and binomial coefficients are nonnegative.
    draw_mass = sum(comb(sum(capacities), k) for k in range(max(0, max_drawn + 1)))
    limb_bits = ((2**63 - 1) // max(1, draw_mass) + 1).bit_length() - 1
    if limb_bits < 1:
        raise OverflowError("Batch land subset counts exceed int64; use backend='scalar'")
    limb_mask = (1 << limb_bits) - 1
    costs = progress(copies) if progress is not None else copies
    for cost in costs:
        generic = int(cost.rstrip("WUBRG") or 0)
        colored = cost[len(str(generic)):] if generic else cost.lstrip("0")
        _, caps = requirements(generic, colored)
        if not copies[cost] or caps[0] > max_drawn or not nonlands:
            yield cost, (Fraction(),) * len(candidates)
            continue
        scenarios = {}
        rows = payment_scenarios(model, generic, colored)
        for turn, seen in seen_by_turn:
            limit, partitions = rows[turn - 1]
            if limit is not None and caps[0] > limit:
                continue
            for scenario in partitions:
                factors = scenarios.setdefault(scenario, [Fraction()] * (max_drawn + 1))
                for k in range(caps[0], max_drawn + 1):
                    if 0 <= seen - k - 1 < nonlands:
                        factors[k] += Fraction(comb(nonlands - 1, seen - k - 1),
                                               comb(deck_size, seen) * len(sides)) * turn_weights[turn - 1]
        if not scenarios:
            yield cost, (Fraction(),) * len(candidates)
            continue
        values, denominator = _opportunity_grid(counts, totals, scenarios, caps, max_drawn)
        numerators = [0] * len(candidates)
        for shift in range(0, denominator.bit_length(), limb_bits):
            digits = np.asarray((values >> shift) & limb_mask, dtype=np.int64)
            if not digits.any():
                continue
            transformed = binomial_transform(digits, max_drawn=max_drawn)
            selected = np.atleast_1d(transformed[indices])
            numerators = [a + (int(b) << shift) for a, b in zip(numerators, selected)]
        yield cost, tuple(copies[cost] * Fraction(n, denominator) for n in numerators)
