"""Reusable component tables, exact weighted scores, and ranking."""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property
from heapq import nsmallest
from math import isfinite, lcm
from numbers import Real
from typing import Literal

from mtg_tools.mana.evaluation import LandSwap, RankedBase, evaluate
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.model import CompiledManaModel, ManaModel
from mtg_tools.mana.sensitivity import Sensitivity, crossings
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.spells import Spell, SpellCost, spell_components
from mtg_tools.mana.timing import resolve_timing


def _fraction(value: Real) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError("Weights must be finite nonnegative numbers")
    return value if isinstance(value, Fraction) else Fraction(str(value))


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
        return crossings(self, parameter, baseline=baseline)


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
            from mtg_tools.mana._batch import component_columns
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
