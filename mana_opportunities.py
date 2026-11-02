"""Draw-based casting opportunities, with independent copies and optimistic land selection.

No sequencing or spells are played out: each drawn copy scores on every turn
its cost is payable, independently of all other copies and costs. Every source
produces one mana, with no tapped entry, life costs, or conditional production.

Example (run with ``python -m doctest mana_opportunities.py``)::

    >>> base = {ManaSource("U", "basic"): 12, ManaSource("UB", "dual"): 12}
    >>> result = evaluate(base, [SpellCost("UU", 20), SpellCost("1B", 16, weight=2)])
    >>> result.score > 0
    True

The raw score is mean weighted opportunities per turn, not a probability.
Penalties are charged per land in the base, after averaging turns/positions.
"""

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import comb, fsum, isfinite
from numbers import Real
from typing import Literal

COLORS = "WUBRG"


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
class ManaSource:
    colors: str
    kind: Literal["basic", "dual", "rainbow"]

    def __post_init__(self) -> None:
        sizes = {"basic": 1, "dual": 2, "rainbow": 5}
        if (self.kind not in sizes or not isinstance(self.colors, str)
                or len(self.colors) != sizes[self.kind] or len(set(self.colors)) != len(self.colors)
                or set(self.colors) - set(COLORS)):
            raise ValueError("Sources require one basic color, two dual colors, or all five rainbow colors")
        object.__setattr__(self, "colors", "".join(c for c in COLORS if c in self.colors))


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
class Opportunity:
    cost: str
    turn: int
    position: Literal["play", "draw"]
    expected_copies: Fraction
    weighted_contribution: float


@dataclass(frozen=True)
class OpportunityResult:
    opportunities: tuple[Opportunity, ...]
    raw_score: float
    penalty: float
    score: float


@lru_cache(maxsize=128)
def _payable_land_weights(sources: tuple[tuple[str, int], ...], generic: int,
                          colored: str, max_drawn: int) -> tuple[int, ...]:
    """Binomial-weighted land draws by size, using capped Hall supply states.

    Every subset of required colors must have at least as many distinct
    available sources as required pips. Capping supplies merges equivalent
    states; irrelevant and interchangeable sources are grouped before the DP.
    """
    required = Counter(colored)
    colors = tuple(required)
    groups = [tuple(c for i, c in enumerate(colors) if mask & (1 << i))
              for mask in range(1, 1 << len(colors))]
    caps = tuple(sum(required[c] for c in group) for group in groups)
    supplies = Counter()
    for options, count in sources:
        supplies[tuple(int(any(c in options for c in group)) for group in groups)] += count

    states = {(0, (0,) * len(caps)): 1}
    for supply, count in supplies.items():
        next_states = defaultdict(int)
        binomials = [comb(count, take) for take in range(min(count, max_drawn) + 1)]
        for (drawn, covered), weight in states.items():
            for take in range(min(count, max_drawn - drawn) + 1):
                updated = tuple(min(cap, have + take * adds) for cap, have, adds in zip(caps, covered, supply))
                next_states[drawn + take, updated] += weight * binomials[take]
        states = next_states

    payable = [0] * (max_drawn + 1)
    for (drawn, covered), weight in states.items():
        if drawn >= generic + len(colored) and covered == caps:
            payable[drawn] += weight
    return tuple(payable)


def evaluate(mana_base: Mapping[ManaSource, int], spells: Sequence[SpellCost], *, turns: int = 7,
             position: Literal["both", "play", "draw"] = "both", opening_hand_size: int = 7,
             rainbow_penalty: float = 0, dual_penalty: float = 0) -> OpportunityResult:
    """Score the full draw distribution, including hands short on lands.

    Deck size is inferred. On turn T see opening_hand_size + T - 1 cards on
    the play, or one more on the draw, capped at deck size. Costs may select
    different lands and are never competing for mana. No turn schedule or
    normalization by spell count/weight is applied.
    """
    _count(turns, "Turn limit")
    _count(opening_hand_size, "Opening hand size")
    if not turns or position not in ("both", "play", "draw"):
        raise ValueError("Turn limit must be positive and position must be both, play, or draw")
    rainbow_penalty = _weight(rainbow_penalty, "Rainbow penalty")
    dual_penalty = _weight(dual_penalty, "Dual penalty")

    sources = Counter()
    penalties = []
    for source, count in mana_base.items():
        if not isinstance(source, ManaSource):
            raise ValueError("Mana base keys must be ManaSource inputs")
        _count(count, "Land count")
        if count:
            sources[source.colors] += count
        penalties.append(count * {"basic": 0, "dual": dual_penalty, "rainbow": rainbow_penalty}[source.kind])
    counts = Counter()
    weighted_counts = defaultdict(list)
    for spell in spells:
        if not isinstance(spell, SpellCost):
            raise ValueError("Spells must be SpellCost inputs")
        counts[spell.cost] += spell.count
        weighted_counts[spell.cost].append(spell.count * float(spell.weight))

    nonlands = sum(counts.values())
    deck_size = sum(sources.values()) + nonlands
    if not deck_size:
        raise ValueError("Deck must contain at least one card")
    positions = ("play", "draw") if position == "both" else (position,)
    max_seen = min(deck_size, max(opening_hand_size + turns - (side == "play") for side in positions))
    max_lands = min(sum(sources.values()), max(0, max_seen - 1))
    source_key = tuple(sorted(sources.items()))
    rows = []
    for cost, copies in counts.items():
        generic, colored = _parse_cost(cost)
        total = generic + len(colored)
        weights = (_payable_land_weights(source_key, generic, colored, max_lands)
                   if copies and total <= turns else ())
        weighted_copies = fsum(weighted_counts[cost])
        for turn in range(1, turns + 1):
            for side in positions:
                seen = min(deck_size, opening_hand_size + turn - (side == "play"))
                # Mark one physical spell: choose the remaining nonlands and
                # lands around it. Multiplying by copies counts every backup.
                numerator = sum(land_weight * comb(nonlands - 1, seen - k - 1)
                                for k, land_weight in enumerate(weights)
                                if 0 <= seen - k - 1 <= nonlands - 1) if total <= turn else 0
                per_copy = Fraction(numerator, comb(deck_size, seen))
                rows.append(Opportunity(cost, turn, side, copies * per_copy, weighted_copies * float(per_copy)))

    raw_score = fsum(row.weighted_contribution for row in rows) / (turns * len(positions))
    penalty = fsum(penalties)
    return OpportunityResult(tuple(rows), raw_score, penalty, raw_score - penalty)
