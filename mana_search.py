"""Reusable opportunity components, bounded exhaustive search, and one-swap sensitivity.

Tables hold exact mean opportunities, independent of importance and penalties.
Crossings vary one absolute cost weight or penalty over the nonnegative domain.
All guarantees refer only to the candidates in the table.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import Literal

from hands import compositions
from mana_opportunities import ManaSource, Spell, SpellCost, evaluate, spell_components

Mode = Literal["exhaustive", "one_swap"]


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
        bounds = dict(sorted(self.bounds.items(), key=lambda item: (item[0].kind, item[0].colors)))
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

    def one_swap(self, baseline: Mapping[ManaSource, int]) -> Iterator[tuple[int, ...]]:
        counts = self.counts(baseline)
        yield counts
        for i, (low, _) in enumerate(self.bounds.values()):
            for j, (_, high) in enumerate(self.bounds.values()):
                if i != j and counts[i] > low and counts[j] < high:
                    candidate = list(counts)
                    candidate[i] -= 1
                    candidate[j] += 1
                    yield tuple(candidate)

    def one_swap_count(self, baseline: Mapping[ManaSource, int]) -> int:
        """Count the baseline and its legal single replacements."""
        counts = self.counts(baseline)
        return 1 + sum(i != j and counts[i] > low and counts[j] < high
                       for i, (low, _) in enumerate(self.bounds.values())
                       for j, (_, high) in enumerate(self.bounds.values()))


@dataclass(frozen=True)
class BaseComponents:
    counts: tuple[int, ...]
    opportunities: tuple[Fraction, ...]
    dual_count: int
    rainbow_count: int


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
class PairwiseCrossing:
    counts: tuple[int, ...]
    delta_at_current: Fraction
    tie_at: Fraction | None
    better: Literal["above", "below", "always", "never", "tied"]
    swap: LandSwap


@dataclass(frozen=True)
class Transition:
    value: Fraction
    counts: tuple[int, ...]
    swap: LandSwap
    optimal_interval: Interval


@dataclass(frozen=True)
class Sensitivity:
    mode: Mode
    parameter: str
    current_value: Fraction
    baseline: tuple[int, ...]
    baseline_is_optimal: bool
    optimal_interval: Interval | None
    lower: Transition | None
    upper: Transition | None
    comparisons: tuple[PairwiseCrossing, ...]


def _optimal_interval(lines: Sequence[tuple[Fraction, Fraction]], index: int) -> Interval | None:
    a, b = lines[index]
    lower, upper = Fraction(0), None
    for aa, bb in lines:
        intercept, slope = aa - a, bb - b
        if not slope:
            if intercept > 0:
                return None
        elif slope > 0:
            bound = -intercept / slope
            upper = bound if upper is None else min(upper, bound)
        else:
            lower = max(lower, -intercept / slope)
    return None if upper is not None and upper < lower else Interval(lower, upper)


@dataclass(frozen=True)
class ComponentTable:
    space: ManaSpace
    costs: tuple[str, ...]
    default_weights: tuple[Fraction, ...]
    rows: tuple[BaseComponents, ...]
    mode: Mode
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

    def _score_rows(self, weights: tuple[Fraction, ...], dual: Fraction,
                    rainbow: Fraction) -> tuple[tuple[Fraction, Fraction, Fraction], ...]:
        values = []
        for row in self.rows:
            raw = sum((w * value for w, value in zip(weights, row.opportunities)), Fraction())
            penalty = dual * row.dual_count + rainbow * row.rainbow_count
            values.append((raw, penalty, raw - penalty))
        return tuple(values)

    def rank(self, weights: Mapping[str, Real] | None = None, *, dual_penalty: Real = 0,
             rainbow_penalty: Real = 0) -> tuple[RankedBase, ...]:
        """Rescore without draw calculations; ties use canonical source-count order."""
        weights = self._weights(weights)
        dual, rainbow = _fraction(dual_penalty), _fraction(rainbow_penalty)
        values = self._score_rows(weights, dual, rainbow)
        baseline_score = next((score for row, (_, _, score) in zip(self.rows, values)
                               if row.counts == self.baseline), None)
        ranked = [RankedBase(row.counts, raw, penalty, score,
                             score - baseline_score if baseline_score is not None else None,
                             self._swap(self.baseline, row.counts) if self.baseline is not None else None)
                  for row, (raw, penalty, score) in zip(self.rows, values)]
        return tuple(sorted(ranked, key=lambda row: (-row.score, row.counts)))

    def crossings(self, parameter: str, *, baseline: Mapping[ManaSource, int] | None = None,
                  weights: Mapping[str, Real] | None = None, dual_penalty: Real = 0,
                  rainbow_penalty: Real = 0) -> Sensitivity:
        """Vary one absolute weight/penalty, holding all other parameters fixed.

        Default reference is the supplied one-swap baseline, or the current
        winner for exhaustive tables. Nonoptimal references still receive
        pairwise comparisons, but have no next-optimum transitions.
        """
        weights_vector = self._weights(weights)
        dual, rainbow = _fraction(dual_penalty), _fraction(rainbow_penalty)
        if parameter in ("dual_penalty", "rainbow_penalty"):
            current = dual if parameter == "dual_penalty" else rainbow
            slopes = tuple(-getattr(row, parameter.replace("penalty", "count")) for row in self.rows)
        else:
            parameter = SpellCost(parameter, 0).cost
            if parameter not in self.costs:
                raise ValueError("Parameter must be a cost in the table or a dual/rainbow penalty")
            index = self.costs.index(parameter)
            current = weights_vector[index]
            slopes = tuple(row.opportunities[index] for row in self.rows)
        scores = {row.counts: value[2]
                  for row, value in zip(self.rows, self._score_rows(weights_vector, dual, rainbow))}
        winner = min(scores, key=lambda counts: (-scores[counts], counts))
        reference = (self.space.counts(baseline) if baseline is not None
                     else self.baseline if self.baseline is not None else winner)
        indices = {row.counts: i for i, row in enumerate(self.rows)}
        if reference not in indices:
            raise ValueError("Baseline must be one of the evaluated candidates")
        baseline_index = indices[reference]
        lines = tuple((scores[row.counts] - slope * current, Fraction(slope))
                      for row, slope in zip(self.rows, slopes))
        a, b = lines[baseline_index]
        comparisons = []
        for row, (aa, bb) in zip(self.rows, lines):
            if row.counts == reference:
                continue
            intercept, slope = aa - a, bb - b
            root = -intercept / slope if slope else None
            tie_at = root if root is not None and root >= 0 else None
            if not slope:
                better = "always" if intercept > 0 else "never" if intercept < 0 else "tied"
            elif slope > 0:
                better = "always" if root < 0 else "above"
            else:
                better = "below" if root > 0 else "never"
            comparisons.append(PairwiseCrossing(row.counts, intercept + slope * current, tie_at,
                                                 better, self._swap(reference, row.counts)))
        optimal = scores[reference] == scores[winner]
        interval = _optimal_interval(lines, baseline_index)

        def transition(value: Fraction | None, direction: int) -> Transition | None:
            if not optimal or value is None or (direction < 0 and value == 0):
                return None
            winning_value = a + b * value
            tied = [i for i, (aa, bb) in enumerate(lines) if aa + bb * value == winning_value]
            successor = min(tied, key=lambda i: (-direction * lines[i][1],
                            self._swap(reference, self.rows[i].counts).cards_replaced, self.rows[i].counts))
            counts = self.rows[successor].counts
            return Transition(value, counts, self._swap(reference, counts), _optimal_interval(lines, successor))

        return Sensitivity(self.mode, parameter, current, reference, optimal, interval,
                           transition(interval.lower, -1) if interval else None,
                           transition(interval.upper, 1) if interval else None, tuple(comparisons))


def build_component_table(space: ManaSpace, spells: Sequence[SpellCost | Spell], *, mode: Mode = "exhaustive",
                          baseline: Mapping[ManaSource, int] | None = None, turns: int = 7,
                          position: Literal["both", "play", "draw"] = "both",
                          opening_hand_size: int = 7,
                          progress: Callable[[Iterable[tuple[int, ...]]], Iterable[tuple[int, ...]]] | None = None
                          ) -> ComponentTable:
    """Evaluate each legal candidate once. Bounds and fixed land count are caller supplied.

    Exhaustive construction is explicit: call space.candidate_count() first
    when sizing a large pool. One-swap tables include the original base and
    its legal neighbors only, without repeated hill climbing. A progress wrapper
    may observe the candidates; it must yield each candidate once, in order.
    """
    if mode not in ("exhaustive", "one_swap") or (mode == "one_swap" and baseline is None):
        raise ValueError("Choose exhaustive, or one_swap with a baseline")
    _, copies, weighted = spell_components(spells)
    costs = tuple(sorted(copies))
    defaults = tuple(weighted[cost] / copies[cost] if copies[cost] else Fraction(1) for cost in costs)
    unweighted = tuple(Spell(s.count, s.modes) if isinstance(s, Spell) else SpellCost(s.cost, s.count)
                       for s in spells)
    reference = space.counts(baseline) if baseline is not None else None
    candidates = space.exhaustive() if mode == "exhaustive" else space.one_swap(baseline)
    if progress is not None:
        candidates = progress(candidates)
    rows = []
    for counts in candidates:
        base = dict(zip(space.sources, counts))
        result = evaluate(base, unweighted, turns=turns, position=position, opening_hand_size=opening_hand_size)
        totals = Counter()
        for opportunity in result.opportunities:
            totals[opportunity.cost] += opportunity.expected_copies
        divisor = turns * (2 if position == "both" else 1)
        rows.append(BaseComponents(counts, tuple(totals[cost] / divisor for cost in costs),
                                  sum(n for s, n in base.items() if s.kind == "dual"),
                                  sum(n for s, n in base.items() if s.kind == "rainbow")))
    return ComponentTable(space, costs, defaults, tuple(rows), mode, reference)
