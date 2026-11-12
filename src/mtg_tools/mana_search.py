"""Reusable opportunity components, local/exhaustive search, and exact sensitivity.

Tables hold exact mean opportunities, independent of spell importance.
Crossings vary one absolute casting-cost weight over the nonnegative domain.
All guarantees refer only to the candidates in the table.
"""

from mtg_tools.mana_timing import resolve_timing

from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from functools import cached_property
from heapq import nsmallest
from itertools import combinations_with_replacement
from math import isfinite, lcm
from numbers import Real
from time import perf_counter
from types import MappingProxyType
from typing import Literal

from mtg_tools.hands import compositions
from mtg_tools.mana_lands import ManaSource, sources_for_colors
from mtg_tools.mana_model import CompiledManaModel, ManaModel
from mtg_tools.mana_opportunities import OpportunityResult, Spell, SpellCost, evaluate, spell_components


def _fraction(value: Real) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError("Weights must be finite nonnegative numbers")
    return value if isinstance(value, Fraction) else Fraction(str(value))


@dataclass(frozen=True)
class ManaSpace:
    bounds: Mapping[ManaSource, tuple[int, int]]
    land_count: int
    family_bounds: Mapping[str, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def from_colors(cls, land_count: int, colors: str, *,
                    families: Mapping[str, tuple[int, int]],
                    format: Literal["standard"] | None = None,
                    fixed: Mapping[ManaSource, int] | None = None,
                    overrides: Mapping[ManaSource, tuple[int, int]] | None = None,
                    family_bounds: Mapping[str, tuple[int, int]] | None = None) -> "ManaSpace":
        """Derive source bounds from explicit colors and opt-in family bounds.

        families assigns bounds per source; family_bounds limits summed copies
        within each selected family. Exact totals use (n, n). Fixed sources count
        toward these aggregate limits.

        Overrides replace bounds for selected sources. Colors constrain eligible
        lands, not the colors every candidate must produce. Optional format filtering
        uses the centralized catalog's dated legality snapshot. Fixed sources may
        belong to families omitted from the flexible pool; their exact counts
        replace family bounds and are included in land_count, not added to it.
        """
        sources = sources_for_colors(colors, families, format=format)
        for limits in families.values():
            if (len(limits) != 2 or any(type(n) is not int for n in limits)
                    or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Supply a (minimum, maximum) integer pair per generated source")
        bounds = {source: families[source.kind] for source in sources}
        if fixed is not None and overrides is not None and set(fixed).intersection(overrides):
            raise ValueError("A source cannot have both fixed counts and overrides")
        if overrides is not None:
            if set(overrides) - set(bounds):
                raise ValueError("Overrides contain sources outside the selected pool")
            bounds.update(overrides)
        for source, count in (fixed or {}).items():
            if not isinstance(source, ManaSource) or type(count) is not int or count < 0:
                raise ValueError("Fixed lands require ManaSource keys and nonnegative integer counts")
            if source not in sources_for_colors(colors, (source.kind,), format=format):
                raise ValueError("Fixed source is outside the selected colors or format")
            bounds[source] = (count, count)
        return cls(bounds, land_count, {} if family_bounds is None else family_bounds)

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
        object.__setattr__(self, "bounds", MappingProxyType({source: tuple(limits) for source, limits in bounds.items()}))
        families = dict(self.family_bounds)
        kinds = {source.kind for source in bounds}
        for kind, limits in families.items():
            if (kind not in kinds or not isinstance(limits, (tuple, list)) or len(limits) != 2
                    or any(type(n) is not int for n in limits) or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Family bounds require selected families and nonnegative integer (minimum, maximum) pairs")
        object.__setattr__(self, "family_bounds", MappingProxyType({kind: tuple(limits) for kind, limits in sorted(families.items())}))
        if any(low > high for _, low, high in self._groups) or not (
                sum(low for _, low, _ in self._groups) <= self.land_count <=
                sum(high for _, _, high in self._groups)):
            raise ValueError("Family bounds are infeasible with source bounds and land count")

    @cached_property
    def _groups(self):
        groups = []
        for kind in sorted({source.kind for source in self.sources}):
            indices = tuple(i for i, source in enumerate(self.sources) if source.kind == kind)
            low = sum(self.bounds[self.sources[i]][0] for i in indices)
            high = sum(self.bounds[self.sources[i]][1] for i in indices)
            minimum, maximum = self.family_bounds.get(kind, (low, high))
            groups.append((indices, max(low, minimum), min(high, maximum)))
        return tuple(groups)

    def _eligible(self, counts):
        return all(low <= sum(counts[i] for i in indices) <= high for indices, low, high in self._groups)


    @property
    def sources(self) -> tuple[ManaSource, ...]:
        return tuple(self.bounds)

    def counts(self, base: Mapping[ManaSource, int]) -> tuple[int, ...]:
        if set(base) - set(self.bounds):
            raise ValueError("Base contains sources outside the pool")
        counts = tuple(base.get(source, 0) for source in self.sources)
        if (any(type(n) is not int or not lo <= n <= hi
                for n, (lo, hi) in zip(counts, self.bounds.values())) or sum(counts) != self.land_count or not self._eligible(counts)):
            raise ValueError("Base is outside the land count, source bounds or family bounds")
        return counts

    def candidate_count(self) -> int:
        """Count legal bases without enumerating or evaluating them."""
        ways = [1] + [0] * self.land_count
        for indices, minimum, maximum in self._groups:
            group = [1] + [0] * self.land_count
            for i in indices:
                low, high = self.bounds[self.sources[i]]
                group = [sum(group[t-n] for n in range(low, min(high, t)+1))
                         for t in range(self.land_count+1)]
            ways = [sum(ways[t-n] * group[n] for n in range(minimum, min(maximum, t)+1))
                    for t in range(self.land_count+1)]
        return ways[self.land_count]

    def exhaustive(self) -> Iterator[tuple[int, ...]]:
        if not self.family_bounds:
            lower = tuple(lo for lo, _ in self.bounds.values())
            capacities = tuple(hi-lo for lo, hi in self.bounds.values())
            for extra in compositions(capacities, self.land_count-sum(lower)):
                yield tuple(lo+n for lo,n in zip(lower,extra))
            return
        groups = self._groups
        counts = [0] * len(self.sources)

        def visit(index, remaining):
            if index == len(groups):
                if remaining == 0:
                    yield tuple(counts)
                return
            indices, minimum, maximum = groups[index]
            tail_low = sum(lo for _,lo,_ in groups[index+1:])
            tail_high = sum(hi for _,_,hi in groups[index+1:])
            lower = tuple(self.bounds[self.sources[i]][0] for i in indices)
            capacities = tuple(self.bounds[self.sources[i]][1]-n for i,n in zip(indices,lower))
            for total in range(max(minimum,remaining-tail_high), min(maximum,remaining-tail_low)+1):
                for extra in compositions(capacities,total-sum(lower)):
                    for i,n,lo in zip(indices,extra,lower):
                        counts[i] = lo+n
                    yield from visit(index+1,remaining-total)
        yield from visit(0,self.land_count)



@dataclass(frozen=True)
class BaseComponents:
    counts: tuple[int, ...]
    opportunities: tuple[Fraction, ...]

    def __setstate__(self, state):
        if set(state) != {'counts', 'opportunities'}:
            raise ValueError("Incompatible component row; rebuild the table")
        for name, value in state.items():
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class LandSwap:
    out: tuple[tuple[ManaSource, int], ...]
    incoming: tuple[tuple[ManaSource, int], ...]
    cards_replaced: int


@dataclass(frozen=True)
class RankedBase:
    counts: tuple[int, ...]
    score: Fraction
    delta: Fraction | None
    swap: LandSwap | None

    def __setstate__(self, state):
        if set(state) != set(self.__dataclass_fields__):
            raise ValueError("Incompatible ranked result; rebuild it")
        for name, value in state.items():
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class LocalNeighborhood:
    current: RankedBase
    neighbors: tuple[RankedBase, ...]
    complete: bool


@dataclass(frozen=True)
class LocalSearchResult:
    baseline: RankedBase
    best: RankedBase
    moves: tuple[RankedBase, ...]
    evaluations: int
    seconds: float
    stopped: str


class LocalManaEvaluator:
    """Exact, lazy per-base evaluation; configuration is immutable, cache is reusable.

    Optional half_life derives a horizon and normalized weights from tail_tolerance.
    Opportunities retain cost/turn/position axes. All composition constraints
    belong to the supplied ManaSpace; scores measure only casting opportunities.
    """

    def __init__(self, space: ManaSpace, spells: Sequence[SpellCost | Spell], *,
                 model: ManaModel | CompiledManaModel, turns: int | None = None,
                 half_life: Real | None = None, tail_tolerance: Real = 0.05,
                 position: Literal["both", "play", "draw"] = "both", opening_hand_size: int = 7):
        self._timing = resolve_timing(turns=turns, half_life=half_life, tail_tolerance=tail_tolerance)
        turns = self.timing.horizon
        if (type(turns) is not int or turns < 1 or type(opening_hand_size) is not int
                or opening_hand_size < 0 or position not in ("both", "play", "draw")):
            raise ValueError("Positive turns, nonnegative opening size, and valid position required")
        self._space, self._spells = space, tuple(spells)
        self._turns, self._position, self._opening = turns, position, opening_hand_size
        self._model = model.compile(space.sources, turns)
        nonlands, copies, weighted = spell_components(self._spells)
        if not nonlands + space.land_count:
            raise ValueError("Deck must contain at least one card")
        self._weights = {c: weighted[c] / n if n else Fraction() for c, n in copies.items()}
        self._cache: dict[tuple[int, ...], OpportunityResult] = {}

    @property
    def timing(self):
        """Resolved, immutable turn horizon and normalized weights."""
        return self._timing

    @property
    def model(self) -> CompiledManaModel:
        return self._model

    @property
    def cache_signature(self) -> tuple:
        """Persist alongside cache entries; includes resolved policy and draw configuration."""
        return ("raw-score-v2", self.timing.signature, self._model.signature, tuple(self.space.bounds.items()), self.space.land_count,
                self._spells, self._position, self._opening, tuple(self.space.family_bounds.items()))

    def restore_cache(self, signature: tuple,
                      entries: Mapping[tuple[int, ...], OpportunityResult]) -> None:
        """Restore a trusted persisted cache only when its full configuration matches."""
        if signature != self.cache_signature:
            raise ValueError("Incompatible mana evaluation cache; rebuild its components")
        self._cache.update(entries)

    @property
    def space(self) -> ManaSpace:
        return self._space

    @property
    def cache(self) -> Mapping[tuple[int, ...], OpportunityResult]:
        return MappingProxyType(self._cache)

    def components(self, base: Mapping[ManaSource, int]) -> OpportunityResult:
        counts = self.space.counts(base)
        if counts not in self._cache:
            self._cache[counts] = evaluate(dict(zip(self.space.sources, counts)), self._spells,
                                          model=self._model,
                                          turns=self._turns if self.timing.half_life is None else None,
                                          half_life=self.timing.half_life,
                                          tail_tolerance=self.timing.tail_tolerance or 0.05,
                                          position=self._position, opening_hand_size=self._opening)
        return self._cache[counts]

    def value(self, base: Mapping[ManaSource, int]) -> RankedBase:
        counts = self.space.counts(base)
        components = self.components(base)
        divisor = 2 if self._position == "both" else 1
        score = sum((row.expected_copies * self._weights[row.cost] * self.timing.weights[row.turn-1]
                     for row in components.opportunities), Fraction()) / divisor
        return RankedBase(counts, score, None, None)

    def _relative(self, reference: RankedBase, value: RankedBase) -> RankedBase:
        out = tuple((s, a-b) for s, a, b in zip(self.space.sources, reference.counts, value.counts) if a > b)
        incoming = tuple((s, b-a) for s, a, b in zip(self.space.sources, reference.counts, value.counts) if b > a)
        return RankedBase(value.counts, value.score,
                          value.score - reference.score, LandSwap(out, incoming, sum(n for _, n in out)))

    def neighbor_counts(self, base: Mapping[ManaSource, int], *,
                        max_replacements: int = 1) -> tuple[tuple[int, ...], ...]:
        """Legal bases within one or two land replacements, deduplicated and sorted.

        Only final compositions must satisfy family totals/maximums. This permits
        coupled moves whose individual transfers would violate an exact total.
        No probabilities or exhaustive composition grid are evaluated here.
        """
        if type(max_replacements) is not int or max_replacements not in (1, 2):
            raise ValueError("Maximum replacements must be 1 or 2")
        counts = self.space.counts(base)
        limits = tuple(self.space.bounds.values())
        candidates = set()
        for size in range(1, max_replacements + 1):
            for remove in combinations_with_replacement(range(len(counts)), size):
                residual = list(counts)
                for i in remove:
                    residual[i] -= 1
                if any(n < lo for n, (lo, _) in zip(residual, limits)):
                    continue
                for add in combinations_with_replacement(range(len(counts)), size):
                    candidate = residual.copy()
                    for i in add:
                        candidate[i] += 1
                    if any(n > hi for n, (_, hi) in zip(candidate, limits)):
                        continue
                    candidate = tuple(candidate)
                    if candidate != counts and self.space._eligible(candidate):
                        candidates.add(candidate)
        return tuple(sorted(candidates))

    def value_and_swap_deltas(self, base: Mapping[ManaSource, int], *, evaluation_budget: int | None = None,
                              max_replacements: int = 1,
                              _visited: set[tuple[int, ...]] | None = None) -> LocalNeighborhood:
        """Score a one- or two-land neighborhood in canonical order.

        Budget counts distinct bases considered, including cached ones and the
        reference. The search shares its visited set between neighborhoods.
        """
        if evaluation_budget is not None and (type(evaluation_budget) is not int or evaluation_budget < 1):
            raise ValueError("Evaluation budget must be a positive integer or None")
        visited = set() if _visited is None else _visited
        counts = self.space.counts(base)
        candidates = self.neighbor_counts(base, max_replacements=max_replacements)
        current = self.value(base)
        visited.add(counts)
        neighbors = []
        complete = True
        for candidate in candidates:
            if candidate not in visited and evaluation_budget is not None and len(visited) >= evaluation_budget:
                complete = False
                break
            value = self.value(dict(zip(self.space.sources, candidate)))
            visited.add(candidate)
            neighbors.append(self._relative(current, value))
        return LocalNeighborhood(current, tuple(neighbors), complete)


def local_search(evaluator: LocalManaEvaluator, initial: Mapping[ManaSource, int], *,
                 evaluation_budget: int = 500,
                 max_replacements: int = 2,
                 progress: Callable[[int, RankedBase], None] | None = None) -> LocalSearchResult:
    """One-land descent, followed by a two-land completion check by default.

    An improving completion move resumes one-land descent before checking again.
    Set max_replacements=1 for the cheaper one-land-only search. A certificate
    requires a complete final neighborhood; budget exhaustion never certifies it.

    evaluations counts unique bases visited this run (cache hits included).
    A partial final neighborhood returns the best evaluated base, without a
    local-optimality claim. Move deltas are relative to the preceding base.
    """
    if type(evaluation_budget) is not int or evaluation_budget < 1:
        raise ValueError("Evaluation budget must be a positive integer")
    if type(max_replacements) is not int or max_replacements not in (1, 2):
        raise ValueError("Maximum replacements must be 1 or 2")
    started = perf_counter()
    baseline = evaluator.value(initial)
    current = baseline
    visited: set[tuple[int, ...]] = set()
    moves = []
    radius = 1
    while True:
        neighborhood = evaluator.value_and_swap_deltas(
            dict(zip(evaluator.space.sources, current.counts)), evaluation_budget=evaluation_budget,
            max_replacements=radius, _visited=visited)
        best = min((current, *neighborhood.neighbors), key=lambda row: (-row.score, row.counts))
        improved = best.score > current.score
        if improved:
            moves.append(best)
            current = best
        if progress is not None:
            progress(len(visited), current)
        if not neighborhood.complete:
            stopped = "evaluation budget"
            break
        if improved:
            radius = 1
        elif radius < max_replacements:
            radius = max_replacements
        else:
            stopped = "two-land local optimum" if radius == 2 else "one-land local optimum"
            break
    return LocalSearchResult(baseline, evaluator._relative(baseline, current), tuple(moves),
                             len(visited), perf_counter() - started, stopped)


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
    model_signature: tuple = ()
    timing_signature: tuple = ()
    schema_version: int = 2

    def __setstate__(self, state):
        if (state.get('schema_version') != 2 or not set(self.__dataclass_fields__) <= set(state)
                or set(state) - set(self.__dataclass_fields__) - {'_indices', '_integer_columns'}):
            raise ValueError("Incompatible component table; rebuild it")
        for name, value in state.items():
            object.__setattr__(self, name, value)

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

    def score(self, weights: Mapping[str, Real] | None = None) -> "ScoredTable":
        """Score casting opportunities once with exact integer dot products."""
        weights = self._weights(weights)
        columns = self._integer_columns
        denominator = lcm(*(col.denominator*w.denominator for col,w in zip(columns,weights)))
        scores = [0] * len(self.rows)
        for column, weight in zip(columns, weights):
            factor = weight.numerator * (denominator // (column.denominator*weight.denominator))
            if factor:
                scores = [a+n*factor for a,n in zip(scores,column.numbers)]
        winner = min(range(len(scores)), key=lambda i: (-scores[i], self.rows[i].counts))
        return ScoredTable(self, weights, denominator, tuple(scores), winner)

    def rank(self, weights: Mapping[str, Real] | None = None, *, limit: int | None = None,
             baseline: Mapping[ManaSource, int] | None = None) -> tuple[RankedBase, ...]:
        return self.score(weights).rank(limit=limit, baseline=baseline)

    def crossings(self, parameter: str, *, baseline: Mapping[ManaSource, int] | None = None,
                  weights: Mapping[str, Real] | None = None) -> Sensitivity:
        return self.score(weights).crossings(parameter, baseline=baseline)


@dataclass(frozen=True)
class ScoredTable:
    """Reusable score snapshot. All scans cover the complete candidate pool."""
    table: ComponentTable
    weights: tuple[Fraction, ...]
    denominator: int
    score_numbers: tuple[int, ...]
    winner_index: int

    def __setstate__(self, state):
        if set(state) != set(self.__dataclass_fields__):
            raise ValueError("Incompatible score snapshot; rebuild it")
        for name, value in state.items():
            object.__setattr__(self, name, value)

    def rank(self, *, limit: int | None = None,
             baseline: Mapping[ManaSource, int] | None = None) -> tuple[RankedBase, ...]:
        if limit is not None and (type(limit) is not int or limit < 0):
            raise ValueError("Rank limit must be a nonnegative integer or None")
        table = self.table
        key = lambda i: (-self.score_numbers[i], table.rows[i].counts)
        indices = (sorted(range(len(table.rows)), key=key) if limit is None
                   else nsmallest(limit, range(len(table.rows)), key=key))
        reference_counts = table.space.counts(baseline) if baseline is not None else None
        if reference_counts is not None and reference_counts not in table._indices:
            raise ValueError("Baseline must be one of the evaluated candidates")
        reference = None if reference_counts is None else self.score_numbers[table._indices[reference_counts]]
        result = []
        for i in indices:
            row, score = table.rows[i], self.score_numbers[i]
            result.append(RankedBase(row.counts, Fraction(score, self.denominator),
                          None if reference is None else Fraction(score - reference, self.denominator),
                          None if reference_counts is None else table._swap(reference_counts, row.counts)))
        return tuple(result)

    def crossings(self, parameter: str, *, baseline: Mapping[ManaSource, int] | None = None) -> Sensitivity:
        table = self.table
        parameter = SpellCost(parameter, 0).cost
        if parameter not in table.costs:
            raise ValueError("Parameter must be a table casting cost")
        j = table.costs.index(parameter)
        current = self.weights[j]
        column = table._integer_columns[j]
        slopes, slope_denominator = column.numbers, column.denominator
        reference = (table.space.counts(baseline) if baseline is not None else
                     table.rows[self.winner_index].counts)
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
                          model: ManaModel | CompiledManaModel,
                          turns: int | None = None,
                          half_life: Real | None = None, tail_tolerance: Real = 0.05,
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
    timing = resolve_timing(turns=turns, half_life=half_life, tail_tolerance=tail_tolerance)
    turns = timing.horizon
    if backend not in ("auto", "scalar", "batch"):
        raise ValueError("Backend must be auto, scalar, or batch")
    if (type(turns) is not int or turns < 1 or type(opening_hand_size) is not int or opening_hand_size < 0
            or position not in ("both", "play", "draw")):
        raise ValueError("Positive integer turns, nonnegative integer opening size, and valid position required")
    nonlands, copies, weighted = spell_components(spells)
    if not space.land_count + nonlands:
        raise ValueError("Deck must contain at least one card")
    compiled = model.compile(space.sources, turns)
    costs = tuple(sorted(copies))
    defaults = tuple(weighted[cost] / copies[cost] if copies[cost] else Fraction(1) for cost in costs)
    unweighted = tuple(Spell(s.count, s.modes) if isinstance(s, Spell) else SpellCost(s.cost, s.count)
                       for s in spells)
    candidates = space.exhaustive()
    use_batch = backend in ("auto", "batch")
    if use_batch:
        try:
            from mtg_tools.mana_batch import component_columns
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
                           progress=component_progress, model=compiled, turn_weights=timing.weights))
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
            result = evaluate(base, unweighted, model=compiled, turns=turns, position=position,
                              opening_hand_size=opening_hand_size)
            totals = Counter()
            for opportunity in result.opportunities:
                totals[opportunity.cost] += opportunity.expected_copies * timing.weights[opportunity.turn - 1]
            divisor = 2 if position == "both" else 1
            values = tuple(totals[cost] / divisor for cost in costs)
        rows.append(BaseComponents(counts, values))
    return ComponentTable(space, costs, defaults, tuple(rows), compiled.signature, timing.signature)
