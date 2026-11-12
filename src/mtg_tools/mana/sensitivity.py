"""Exact optimality intervals and casting-cost weight transitions."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import lcm
from typing import TYPE_CHECKING

from mtg_tools.mana.evaluation import LandSwap
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.spells import SpellCost

if TYPE_CHECKING:
    from mtg_tools.mana.tables import ScoredTable


@dataclass(frozen=True)
class Interval:
    """Closed interval of optimality, including ties; None upper means unbounded."""
    lower: Fraction
    upper: Fraction | None


@dataclass(frozen=True)
class Transition:
    value: Fraction
    counts: tuple[int, ...]
    swap: LandSwap
    optimal_interval: Interval


@dataclass(frozen=True)
class Sensitivity:
    parameter: str
    current_value: Fraction
    baseline: tuple[int, ...]
    baseline_is_optimal: bool
    optimal_interval: Interval | None
    lower: Transition | None
    upper: Transition | None


def _integer_interval(lines: Sequence[tuple[int, int, int]], a: int, b: int) -> Interval | None:
    """Intersect exact integer-line inequalities; reduce fractions only at the end."""
    ln, ld, upper = 0, 1, None
    for aa, bb, _ in lines:
        intercept, slope = aa - a, bb - b
        if slope == 0:
            if intercept > 0:
                return None
        elif slope > 0:
            n, d = -intercept, slope
            if upper is None or n * upper[1] < upper[0] * d:
                upper = n, d
        else:
            n, d = intercept, -slope
            if n * ld > ln * d:
                ln, ld = n, d
    if upper is not None and upper[0] * ld < ln * upper[1]:
        return None
    return Interval(Fraction(ln, ld), None if upper is None else Fraction(*upper))


def crossings(scored: "ScoredTable", parameter: str, *, baseline: Mapping[ManaSource, int] | None = None) -> Sensitivity:
    table = scored.table
    parameter = SpellCost(parameter, 0).cost
    if parameter not in table.costs:
        raise ValueError("Parameter must be a table casting cost")
    j = table.costs.index(parameter)
    current = scored.weights[j]
    column = table._integer_columns[j]
    slopes, slope_denominator = column.numbers, column.denominator
    reference = (table.space.counts(baseline) if baseline is not None else
                 table.rows[scored.winner_index].counts)
    if reference not in table._indices:
        raise ValueError("Baseline must be one of the evaluated candidates")
    reference_index = table._indices[reference]

    def preference(i: int) -> tuple[int, tuple[int, ...]]:
        counts = table.rows[i].counts
        return sum(abs(a - b) for a, b in zip(reference, counts)), counts

    # Parallel lines cannot overtake their group's highest line.
    groups = {}
    for i, slope in enumerate(slopes):
        previous = groups.get(slope)
        if (previous is None or scored.score_numbers[i] > scored.score_numbers[previous]
                or (scored.score_numbers[i] == scored.score_numbers[previous]
                    and preference(i) < preference(previous))):
            groups[slope] = i
    common = lcm(scored.denominator, slope_denominator * current.denominator)
    score_factor = common // scored.denominator
    slope_factor = common // slope_denominator
    current_factor = common // (slope_denominator * current.denominator) * current.numerator

    def line(i: int) -> tuple[int, int, int]:
        return (scored.score_numbers[i] * score_factor - slopes[i] * current_factor,
                slopes[i] * slope_factor, i)

    lines = tuple(line(i) for i in groups.values())
    a, b, _ = line(reference_index)
    interval = _integer_interval(lines, a, b)
    optimal = scored.score_numbers[reference_index] == scored.score_numbers[scored.winner_index]

    def transition(value: Fraction | None, direction: int) -> Transition | None:
        if not optimal or value is None or (direction < 0 and value == 0):
            return None
        p, q = value.numerator, value.denominator
        tied = [(aa, bb, i) for aa, bb, i in lines if aa * q + bb * p == a * q + b * p]
        aa, bb, i = min(tied, key=lambda item: (-direction * item[1], *preference(item[2])))
        successor_interval = _integer_interval(lines, aa, bb)
        assert successor_interval is not None
        counts = table.rows[i].counts
        return Transition(value, counts, table._swap(reference, counts), successor_interval)

    return Sensitivity(parameter, current, reference, optimal, interval,
                       transition(interval.lower, -1) if interval else None,
                       transition(interval.upper, 1) if interval else None)
