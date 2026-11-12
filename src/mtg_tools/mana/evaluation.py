"""Draw-based casting opportunities, with independent copies and optimistic land selection.

No sequencing or spells are played out: each drawn copy scores independently.
An explicit model supplies independent source outcomes and the per-turn source
limit. Realized source outcomes jointly supply mana and colors. Production
policies and conditional-color rules live outside this evaluator.

Example (run with ``python -m doctest src/mtg_tools/mana/evaluation.py``)::

    >>> from mtg_tools.mana.policy import heuristic_mana_model
    >>> base = {ManaSource("U", "basic"): 12, ManaSource("UB", "shock"): 12}
    >>> result = evaluate(base, [SpellCost("UU", 20), SpellCost("1B", 16, weight=2)],
    ...                   model=heuristic_mana_model())
    >>> result.score > 0
    True

The score is mean weighted opportunities per turn, not a probability.
"""

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import comb, fsum, lcm
from numbers import Real
from types import MappingProxyType
from typing import Literal

from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.model import CompiledManaModel, ManaModel
from mtg_tools.mana.payment import PaymentScenario, payment_scenarios, requirements
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.spells import Spell, SpellCost, _count, _parse_cost, spell_components
from mtg_tools.mana.timing import resolve_timing


@dataclass(frozen=True)
class Opportunity:
    cost: str
    turn: int
    position: Literal["play", "draw"]
    expected_copies: Fraction
    weighted_contribution: float


@dataclass(frozen=True)
class OpportunityResult:
    opportunities: tuple[Opportunity, ...]
    score: float

    def __setstate__(self, state):
        if set(state) != {'opportunities', 'score'}:
            raise ValueError("Incompatible scoring result; rebuild the cache")
        for name, value in state.items():
            object.__setattr__(self, name, value)


@lru_cache(maxsize=128)
def _land_weights(capacities: tuple[int, ...], scenario: PaymentScenario,
                  caps: tuple[int, ...], max_drawn: int) -> tuple[Fraction, ...]:
    """Draw-weighted joint payment probabilities, with capped Hall supplies."""
    scale = lcm(*(p.denominator for dist in scenario.distributions for _, p in dist))
    groups = Counter()
    allowed = 0
    for context in scenario.contexts:
        allowed |= context
    for count, type_mask, distribution in zip(capacities, scenario.type_masks, scenario.distributions):
        if count and not type_mask & ~allowed:
            groups[type_mask, distribution] += count

    zero = (0,) * len(caps)
    states = {(0, 0, zero): 1}
    for (type_mask, distribution), count in groups.items():
        outcomes = [{zero: 1}]
        for take in range(1, min(count, max_drawn) + 1):
            combined = defaultdict(int)
            for covered, weight in outcomes[-1].items():
                for supply, probability in distribution:
                    updated = tuple(min(cap, have + n) for cap, have, n in zip(caps, covered, supply))
                    combined[updated] += weight * int(probability * scale)
            outcomes.append(combined)
        next_states = defaultdict(int)
        for (drawn, observed, covered), weight in states.items():
            for take in range(min(count, max_drawn - drawn) + 1):
                seen = observed | type_mask if take else observed
                choose = comb(count, take)
                for supply, mass in outcomes[take].items():
                    updated = tuple(min(cap, have + n) for cap, have, n in zip(caps, covered, supply))
                    next_states[drawn + take, seen, updated] += weight * choose * mass
        states = next_states
    payable = [Fraction()] * (max_drawn + 1)
    for (drawn, observed, covered), weight in states.items():
        if observed in scenario.contexts and covered == caps:
            payable[drawn] += Fraction(weight, scale**drawn)
    return tuple(payable)


def evaluate(mana_base: Mapping[ManaSource, int], spells: Sequence[SpellCost | Spell], *,
             model: ManaModel | CompiledManaModel, turns: int | None = None, half_life: Real | None = None,
             tail_tolerance: Real = 0.05,
             position: Literal["both", "play", "draw"] = "both", opening_hand_size: int = 7) -> OpportunityResult:
    """Score the full draw distribution, including hands short on lands.

    Deck size is inferred. On turn T see opening_hand_size + T - 1 cards on
    the play, or one more on the draw, capped at deck size. Costs may select
    different lands and are never competing for mana. No casting sequence or
    normalization by spell count/weight is applied.

    With half_life set, omit turns: the horizon is derived from tail_tolerance
    and scores use normalized exponential weights. Opportunity rows themselves
    remain unweighted. Otherwise turns selects a uniform horizon (default 7).
    """
    timing = resolve_timing(turns=turns, half_life=half_life, tail_tolerance=tail_tolerance)
    turns = timing.horizon
    _count(turns, "Turn limit")
    _count(opening_hand_size, "Opening hand size")
    if not turns or position not in ("both", "play", "draw"):
        raise ValueError("Turn limit must be positive and position must be both, play, or draw")

    sources = Counter()
    for source, count in mana_base.items():
        if not isinstance(source, ManaSource):
            raise ValueError("Mana base keys must be ManaSource inputs")
        _count(count, "Land count")
        sources[source] += count
    nonlands, counts, weighted_counts = spell_components(spells)
    deck_size = sum(sources.values()) + nonlands
    if not deck_size:
        raise ValueError("Deck must contain at least one card")
    positions = ("play", "draw") if position == "both" else (position,)
    max_seen = min(deck_size, max(opening_hand_size + turns - (side == "play") for side in positions))
    max_lands = min(sum(sources.values()), max(0, max_seen - 1))
    source_key = tuple(sorted(sources.items(), key=lambda item: (item[0].kind, item[0].colors, item[0].types)))
    compiled = model.compile(tuple(source for source, _ in source_key), turns)
    capacities = tuple(count for _, count in source_key)
    rows = []
    for cost, copies in counts.items():
        generic, colored = _parse_cost(cost)
        total = generic + len(colored)
        _, caps = requirements(generic, colored)
        scenarios = payment_scenarios(compiled, generic, colored)
        weighted_copies = float(weighted_counts[cost])
        for turn in range(1, turns + 1):
            limit, partitions = scenarios[turn - 1]
            turn_weights = [Fraction()] * (max_lands + 1)
            if copies and (limit is None or total <= limit):
                for scenario in partitions:
                    weights = _land_weights(capacities, scenario, caps, max_lands)
                    turn_weights = [a + b for a, b in zip(turn_weights, weights)]
            for side in positions:
                seen = min(deck_size, opening_hand_size + turn - (side == "play"))
                # Mark one physical spell: choose the remaining nonlands and
                # lands around it. Multiplying by copies counts every backup.
                numerator = sum(land_weight * comb(nonlands - 1, seen - k - 1)
                                for k, land_weight in enumerate(turn_weights)
                                if 0 <= seen - k - 1 <= nonlands - 1)
                per_copy = Fraction(numerator, comb(deck_size, seen))
                rows.append(Opportunity(cost, turn, side, copies * per_copy, weighted_copies * float(per_copy)))

    if timing.half_life is None:
        score = fsum(row.weighted_contribution for row in rows) / (turns * len(positions))
    else:
        score = fsum(row.weighted_contribution * float(timing.weights[row.turn - 1])
                         for row in rows) / len(positions)
    return OpportunityResult(tuple(rows), score)



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
        """Delegate legal neighborhood generation to the search space."""
        return self.space.neighbor_counts(base, max_replacements=max_replacements)

    def value_and_swap_deltas(self, base: Mapping[ManaSource, int], *, evaluation_budget: int | None = None,
                              max_replacements: int = 1,
                              _visited: set[tuple[int, ...]] | None = None) -> LocalNeighborhood:
        """Score a neighborhood using the local search's visit-budget rules."""
        from mtg_tools.mana.local import value_and_swap_deltas

        return value_and_swap_deltas(self, base, evaluation_budget=evaluation_budget,
                                     max_replacements=max_replacements, _visited=_visited)
