"""Reusable opportunity components, exhaustive search, and efficient exact sensitivity.

Tables hold exact mean opportunities, independent of importance and penalties.
Crossings vary one absolute cost weight or penalty over the nonnegative domain.
All guarantees refer only to the candidates in the table.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property
from heapq import nsmallest
from math import isfinite, lcm
from numbers import Real
from types import MappingProxyType
from typing import Literal

from hands import compositions
from mana_opportunities import ManaSource, Spell, SpellCost, evaluate, spell_components


def _fraction(value: Real) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError("Weights and penalties must be finite nonnegative numbers")
    return value if isinstance(value, Fraction) else Fraction(str(value))


@dataclass(frozen=True)
class ManaSpace:
    bounds: Mapping[ManaSource, tuple[int, int]]
    land_count: int

    def __post_init__(self) -> None:
        if type(self.land_count) is not int or self.land_count < 0:
            raise ValueError("Land count must be a nonnegative integer")
        for source, limits in self.bounds.items():
            if (not isinstance(source, ManaSource) or len(limits) != 2
                    or any(type(n) is not int for n in limits) or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Supply a (minimum, maximum) integer pair per ManaSource")
        bounds = dict(sorted(self.bounds.items(), key=lambda item: (item[0].kind, item[0].colors, item[0].types)))
        if not sum(lo for lo, _ in bounds.values()) <= self.land_count <= sum(hi for _, hi in bounds.values()):
            raise ValueError("Land count is infeasible within the bounds")
        object.__setattr__(self, "bounds", MappingProxyType(bounds))

    @property
    def sources(self) -> tuple[ManaSource, ...]:
        return tuple(self.bounds)

    def counts(self, base: Mapping[ManaSource, int]) -> tuple[int, ...]:
        if set(base) - set(self.bounds):
            raise ValueError("Base contains sources outside the pool")
        counts = tuple(base.get(source, 0) for source in self.sources)
        if (any(type(n) is not int or not lo <= n <= hi
                for n, (lo, hi) in zip(counts, self.bounds.values())) or sum(counts) != self.land_count):
            raise ValueError("Base is outside the land count or source bounds")
        return counts

    def candidate_count(self) -> int:
        """Count legal bases without enumerating or evaluating them."""
        ways = [1] + [0] * self.land_count
        for low, high in self.bounds.values():
            ways = [sum(ways[total - n] for n in range(low, min(high, total) + 1))
                    for total in range(self.land_count + 1)]
        return ways[self.land_count]

    def exhaustive(self) -> Iterator[tuple[int, ...]]:
        lower = tuple(lo for lo, _ in self.bounds.values())
        capacities = tuple(hi - lo for lo, hi in self.bounds.values())
        for extra in compositions(capacities, self.land_count - sum(lower)):
            yield tuple(lo + n for lo, n in zip(lower, extra))



@dataclass(frozen=True)
class BaseComponents:
    counts: tuple[int, ...]
    opportunities: tuple[Fraction, ...]
    shock_count: int
    town_count: int


@dataclass(frozen=True)
class LandSwap:
    out: tuple[tuple[ManaSource, int], ...]
    incoming: tuple[tuple[ManaSource, int], ...]
    cards_replaced: int


@dataclass(frozen=True)
class RankedBase:
    counts: tuple[int, ...]
    raw_score: Fraction
    penalty: Fraction
    score: Fraction
    delta: Fraction | None
    swap: LandSwap | None


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


@dataclass(frozen=True)
class IntegerColumn:
    numbers: tuple[int, ...]
    denominator: int


@dataclass(frozen=True)
class ComponentTable:
    space: ManaSpace
    costs: tuple[str, ...]
    default_weights: tuple[Fraction, ...]
    rows: tuple[BaseComponents, ...]
    baseline: tuple[int, ...] | None

    def _weights(self, overrides: Mapping[str, Real] | None) -> tuple[Fraction, ...]:
        weights = dict(zip(self.costs, self.default_weights))
        supplied = set()
        for cost, value in (overrides or {}).items():
            cost = SpellCost(cost, 0).cost
            if cost not in weights or cost in supplied:
                raise ValueError("Weight overrides must identify distinct costs in the table")
            supplied.add(cost)
            weights[cost] = _fraction(value)
        return tuple(weights[cost] for cost in self.costs)

    def _swap(self, before: tuple[int, ...], after: tuple[int, ...]) -> LandSwap:
        out = tuple((s, a - b) for s, a, b in zip(self.space.sources, before, after) if a > b)
        incoming = tuple((s, b - a) for s, a, b in zip(self.space.sources, before, after) if b > a)
        return LandSwap(out, incoming, sum(n for _, n in out))

    @cached_property
    def _indices(self) -> dict[tuple[int, ...], int]:
        return {row.counts: i for i, row in enumerate(self.rows)}

    @cached_property
    def _integer_columns(self) -> tuple[IntegerColumn, ...]:
        columns = []
        for j in range(len(self.costs)):
            denominator = 1
            for row in self.rows:
                denominator = lcm(denominator, row.opportunities[j].denominator)
            numbers = tuple(row.opportunities[j].numerator * (denominator // row.opportunities[j].denominator)
                            for row in self.rows)
            columns.append(IntegerColumn(numbers, denominator))
        return tuple(columns)

    def score(self, weights: Mapping[str, Real] | None = None, *, shock_penalty: Real = 0,
              town_penalty: Real = 0) -> "ScoredTable":
        """Score once with integer dot products; reuse for rankings and crossings."""
        weights = self._weights(weights)
        shock, town = _fraction(shock_penalty), _fraction(town_penalty)
        columns = self._integer_columns
        denominator = lcm(shock.denominator, town.denominator,
                          *(col.denominator * w.denominator for col, w in zip(columns, weights)))
        raw = [0] * len(self.rows)
        for column, weight in zip(columns, weights):
            factor = weight.numerator * (denominator // (column.denominator * weight.denominator))
            if factor:
                raw = [a + n * factor for a, n in zip(raw, column.numbers)]
        shock_factor = shock.numerator * (denominator // shock.denominator)
        town_factor = town.numerator * (denominator // town.denominator)
        scores = tuple(a - shock_factor * row.shock_count - town_factor * row.town_count
                       for a, row in zip(raw, self.rows))
        winner = min(range(len(scores)), key=lambda i: (-scores[i], self.rows[i].counts))
        return ScoredTable(self, weights, shock, town, denominator, tuple(raw), scores, winner)

    def rank(self, weights: Mapping[str, Real] | None = None, *, shock_penalty: Real = 0,
             town_penalty: Real = 0, limit: int | None = None) -> tuple[RankedBase, ...]:
        return self.score(weights, shock_penalty=shock_penalty, town_penalty=town_penalty).rank(limit=limit)

    def crossings(self, parameter: str, *, baseline: Mapping[ManaSource, int] | None = None,
                  weights: Mapping[str, Real] | None = None, shock_penalty: Real = 0,
                  town_penalty: Real = 0) -> Sensitivity:
        return self.score(weights, shock_penalty=shock_penalty, town_penalty=town_penalty).crossings(
            parameter, baseline=baseline)


@dataclass(frozen=True)
class ScoredTable:
    """Reusable score snapshot. All scans cover the complete candidate pool."""
    table: ComponentTable
    weights: tuple[Fraction, ...]
    shock_penalty: Fraction
    town_penalty: Fraction
    denominator: int
    raw_numbers: tuple[int, ...]
    score_numbers: tuple[int, ...]
    winner_index: int

    def rank(self, *, limit: int | None = None) -> tuple[RankedBase, ...]:
        if limit is not None and (type(limit) is not int or limit < 0):
            raise ValueError("Rank limit must be a nonnegative integer or None")
        table = self.table
        key = lambda i: (-self.score_numbers[i], table.rows[i].counts)
        indices = (sorted(range(len(table.rows)), key=key) if limit is None
                   else nsmallest(limit, range(len(table.rows)), key=key))
        reference = None if table.baseline is None else self.score_numbers[table._indices[table.baseline]]
        result = []
        for i in indices:
            row, raw, score = table.rows[i], self.raw_numbers[i], self.score_numbers[i]
            result.append(RankedBase(row.counts, Fraction(raw, self.denominator),
                          Fraction(raw - score, self.denominator), Fraction(score, self.denominator),
                          None if reference is None else Fraction(score - reference, self.denominator),
                          None if table.baseline is None else table._swap(table.baseline, row.counts)))
        return tuple(result)

    def crossings(self, parameter: str, *, baseline: Mapping[ManaSource, int] | None = None) -> Sensitivity:
        table = self.table
        if parameter in ("shock_penalty", "town_penalty"):
            current = getattr(self, parameter)
            slopes = tuple(-getattr(row, parameter.replace("penalty", "count")) for row in table.rows)
            slope_denominator = 1
        else:
            parameter = SpellCost(parameter, 0).cost
            if parameter not in table.costs:
                raise ValueError("Parameter must be a table cost or a shock/town penalty")
            j = table.costs.index(parameter)
            current = self.weights[j]
            column = table._integer_columns[j]
            slopes, slope_denominator = column.numbers, column.denominator
        reference = (table.space.counts(baseline) if baseline is not None else
                     table.baseline if table.baseline is not None else table.rows[self.winner_index].counts)
        if reference not in table._indices:
            raise ValueError("Baseline must be one of the evaluated candidates")
        reference_index = table._indices[reference]

        def preference(i: int) -> tuple[int, tuple[int, ...]]:
            counts = table.rows[i].counts
            return sum(abs(a - b) for a, b in zip(reference, counts)), counts

        # Parallel lines can never overtake their group's highest line. Penalty
        # slopes are land counts, reducing hundreds of thousands of lines to
        # a few dozen without dropping any possible winner or crossing.
        groups = {}
        for i, slope in enumerate(slopes):
            previous = groups.get(slope)
            if (previous is None or self.score_numbers[i] > self.score_numbers[previous]
                    or (self.score_numbers[i] == self.score_numbers[previous]
                        and preference(i) < preference(previous))):
                groups[slope] = i
        common = lcm(self.denominator, slope_denominator * current.denominator)
        score_factor = common // self.denominator
        slope_factor = common // slope_denominator
        current_factor = common // (slope_denominator * current.denominator) * current.numerator

        def line(i: int) -> tuple[int, int, int]:
            return (self.score_numbers[i] * score_factor - slopes[i] * current_factor,
                    slopes[i] * slope_factor, i)

        lines = tuple(line(i) for i in groups.values())
        a, b, _ = line(reference_index)
        interval = _integer_interval(lines, a, b)
        optimal = self.score_numbers[reference_index] == self.score_numbers[self.winner_index]

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


def build_component_table(space: ManaSpace, spells: Sequence[SpellCost | Spell], *,
                          baseline: Mapping[ManaSource, int] | None = None, turns: int = 7,
                          position: Literal["both", "play", "draw"] = "both",
                          opening_hand_size: int = 7,
                          progress: Callable[[Iterable[tuple[int, ...]]], Iterable[tuple[int, ...]]] | None = None,
                          backend: Literal["auto", "scalar", "batch"] = "auto",
                          component_progress: Callable[[Iterable[str]], Iterable[str]] | None = None
                          ) -> ComponentTable:
    """Evaluate each legal candidate once. Bounds and fixed land count are caller supplied.

    Exhaustive construction is explicit: call space.candidate_count() first
    when sizing a large pool. Every legal composition is evaluated. A progress wrapper
    may observe the candidates; it must yield each candidate once, in order.
    Auto batches exhaustive pools when NumPy is available, without size cutoffs.
    Batch work is reported by component_progress;
    progress wraps final candidate-row assembly. Scalar remains the reference.
    """
    if backend not in ("auto", "scalar", "batch"):
        raise ValueError("Backend must be auto, scalar, or batch")
    if (type(turns) is not int or turns < 1 or type(opening_hand_size) is not int or opening_hand_size < 0
            or position not in ("both", "play", "draw")):
        raise ValueError("Positive integer turns, nonnegative integer opening size, and valid position required")
    nonlands, copies, weighted = spell_components(spells)
    if not space.land_count + nonlands:
        raise ValueError("Deck must contain at least one card")
    costs = tuple(sorted(copies))
    defaults = tuple(weighted[cost] / copies[cost] if copies[cost] else Fraction(1) for cost in costs)
    unweighted = tuple(Spell(s.count, s.modes) if isinstance(s, Spell) else SpellCost(s.cost, s.count)
                       for s in spells)
    reference = space.counts(baseline) if baseline is not None else None
    candidates = space.exhaustive()
    use_batch = backend in ("auto", "batch")
    if use_batch:
        try:
            from mana_batch import component_columns
        except ImportError:
            if backend == "batch":
                raise
            use_batch = False
    columns = None
    if use_batch:
        candidates = tuple(candidates)
        try:
            columns = dict(component_columns(space.bounds, space.land_count, copies, candidates,
                           nonlands=nonlands, turns=turns, position=position, opening_hand_size=opening_hand_size,
                           progress=component_progress))
        except OverflowError:
            if backend == "batch":
                raise
            # Unusually large capacities/draw horizons may exceed the exact
            # integer-transform bound. Scalar uses unbounded Python integers.
            columns = None
    if progress is not None:
        candidates = progress(candidates)
    rows = []
    for index, counts in enumerate(candidates):
        base = dict(zip(space.sources, counts))
        if columns is not None:
            values = tuple(columns[cost][index] for cost in costs)
        else:
            result = evaluate(base, unweighted, turns=turns, position=position, opening_hand_size=opening_hand_size)
            totals = Counter()
            for opportunity in result.opportunities:
                totals[opportunity.cost] += opportunity.expected_copies
            divisor = turns * (2 if position == "both" else 1)
            values = tuple(totals[cost] / divisor for cost in costs)
        rows.append(BaseComponents(counts, values,
                                  sum(n for s, n in base.items() if s.kind == "shock"),
                                  sum(n for s, n in base.items() if s.kind == "town")))
    return ComponentTable(space, costs, defaults, tuple(rows), reference)
