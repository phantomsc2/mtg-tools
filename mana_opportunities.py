"""Draw-based casting opportunities, with independent copies and optimistic land selection.

No sequencing or spells are played out: each drawn copy scores independently.
An explicit model supplies independent source outcomes and the per-turn source
limit. Realized source outcomes jointly supply mana and colors. Production
policies and conditional-color rules live outside this evaluator.

Example (run with ``python -m doctest mana_opportunities.py``)::

    >>> from mana_model import heuristic_mana_model
    >>> base = {ManaSource("U", "basic"): 12, ManaSource("UB", "shock"): 12}
    >>> result = evaluate(base, [SpellCost("UU", 20), SpellCost("1B", 16, weight=2)],
    ...                   model=heuristic_mana_model())
    >>> result.score > 0
    True

The score is mean weighted opportunities per turn, not a probability.
"""

from mana_timing import resolve_timing

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import comb, fsum, isfinite, lcm
from numbers import Real
from typing import Literal

from mana_lands import COLORS, ManaSource
from mana_model import CompiledManaModel, ManaModel
from mana_payment import PaymentScenario, payment_scenarios, requirements


def _count(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")


def _weight(value: Real, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite nonnegative number")
    return float(value)


def _parse_cost(cost: str) -> tuple[int, str]:
    if not isinstance(cost, str) or not cost or not re.fullmatch(r"(?:0|[1-9][0-9]*)?[WUBRG]*", cost):
        raise ValueError("Costs must contain optional generic mana followed by WUBRG pips, e.g. 2UU")
    digits = cost.rstrip(COLORS)
    return int(digits or 0), "".join(c * cost.count(c) for c in COLORS)


@dataclass(frozen=True)
class SpellCost:
    cost: str
    count: int
    weight: float = 1

    def __post_init__(self) -> None:
        generic, colored = _parse_cost(self.cost)
        _count(self.count, "Spell count")
        _weight(self.weight, "Spell weight")
        object.__setattr__(self, "cost", (str(generic) if generic else "") + colored or "0")


@dataclass(frozen=True)
class CastingMode:
    cost: str
    weight: float = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "cost", SpellCost(self.cost, 0).cost)
        _weight(self.weight, "Mode weight")


@dataclass(frozen=True)
class Spell:
    count: int
    modes: tuple[CastingMode, ...]
    weight: float = 1

    def __post_init__(self) -> None:
        _count(self.count, "Spell count")
        _weight(self.weight, "Spell weight")
        object.__setattr__(self, "modes", tuple(self.modes))
        if not self.modes or any(not isinstance(m, CastingMode) for m in self.modes):
            raise ValueError("Supply at least one CastingMode")
        if not any(m.weight > 0 for m in self.modes):
            raise ValueError("At least one mode must have positive weight")


def spell_components(spells: Sequence[SpellCost | Spell]) -> tuple[int, Counter, Counter]:
    """Physical nonlands, normalized copy shares, and importance-weighted shares."""
    nonlands = 0
    counts, weighted = Counter(), Counter()
    for spell in spells:
        if not isinstance(spell, (SpellCost, Spell)):
            raise ValueError("Spells must be SpellCost or Spell inputs")
        nonlands += spell.count
        modes = spell.modes if isinstance(spell, Spell) else (CastingMode(spell.cost),)
        total = sum((Fraction(str(m.weight)) for m in modes), Fraction())
        for mode in modes:
            share = spell.count * Fraction(str(mode.weight)) / total
            counts[mode.cost] += share
            weighted[mode.cost] += share * Fraction(str(spell.weight))
    return nonlands, counts, weighted


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
