"""Draw-based casting opportunities, with independent copies and optimistic land selection.

No sequencing or spells are played out: each drawn copy scores on every turn
its cost is payable, independently of all other copies and costs. Town and
Cavern are unrestricted rainbow sources; Cavern restrictions remain excluded.
Every available source produces one mana. Independent land failures model tapped entry;
payment jointly checks mana and colors from successful sources.
life costs are not simulated. Verge secondary colors
use enabling land types anywhere among lands seen, ignoring enabler land drops.

Example (run with ``python -m doctest mana_opportunities.py``)::

    >>> base = {ManaSource("U", "basic"): 12, ManaSource("UB", "shock"): 12}
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
from types import MappingProxyType
from typing import Literal

from mana_lands import COLORS, ManaSource, VERGE_RULES, land_availability


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


@lru_cache(maxsize=128)
def _verge_land_weights(sources: tuple[tuple[ManaSource, int], ...], generic: int,
                        colored: str, max_drawn: int) -> tuple[int, ...]:
    """Capped-supply DP partitioned by enabling types among all lands seen.

    Each draw belongs to exactly one final type mask. For that mask production
    options are fixed, so states need only land count, observed types, and Hall
    supplies. No drawn multisets or selected battlefields are enumerated.
    """
    relevant = set().union(*(set(VERGE_RULES[s.colors].requires) for s, _ in sources
                            if s.kind == "verge" and VERGE_RULES[s.colors].secondary in colored))
    possible = set().union(*(set(s.types) for s, _ in sources))
    types = tuple(c for c in COLORS if c in relevant & possible)
    if not types:
        primary = Counter()
        for source, count in sources:
            primary[source.primary_colors] += count
        return _payable_land_weights(tuple(sorted(primary.items())), generic, colored, max_drawn)

    required = Counter(colored)
    colors = tuple(required)
    groups = [tuple(c for i, c in enumerate(colors) if mask & (1 << i))
              for mask in range(1, 1 << len(colors))]
    caps = tuple(sum(required[c] for c in group) for group in groups)
    payable = [0] * (max_drawn + 1)
    for target in range(1 << len(types)):
        supplies = Counter()
        reachable = 0
        for source, count in sources:
            type_mask = sum(1 << i for i, c in enumerate(types) if c in source.types)
            if type_mask & ~target:
                continue  # This scenario draws zero of this source.
            reachable |= type_mask
            options = source.primary_colors
            if source.kind == "verge":
                rule = VERGE_RULES[source.colors]
                if any(target & (1 << i) for i, c in enumerate(types) if c in rule.requires):
                    options += rule.secondary
            supply = tuple(int(any(c in options for c in group)) for group in groups)
            supplies[supply, type_mask] += count
        if reachable != target:
            continue
        states = {(0, 0, (0,) * len(caps)): 1}
        for (supply, type_mask), count in supplies.items():
            next_states = defaultdict(int)
            binomials = [comb(count, take) for take in range(min(count, max_drawn) + 1)]
            for (drawn, observed, covered), weight in states.items():
                for take in range(min(count, max_drawn - drawn) + 1):
                    updated = tuple(min(cap, have + take * adds) for cap, have, adds in zip(caps, covered, supply))
                    seen_types = observed | type_mask if take else observed
                    next_states[drawn + take, seen_types, updated] += weight * binomials[take]
            states = next_states
        for (drawn, observed, covered), weight in states.items():
            if drawn >= generic + len(colored) and observed == target and covered == caps:
                payable[drawn] += weight
    return tuple(payable)


@lru_cache(maxsize=128)
def _available_land_weights(sources: tuple[tuple[ManaSource, int], ...], generic: int,
                            colored: str, max_drawn: int, rates: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    """Joint payment from independently available lands, weighted over draws.

    Only successes add mana and color coverage. Enabling land types still
    come from all seen lands, preserving the optimistic Verge approximation.
    """
    total = generic + len(colored)
    relevant = set().union(*(set(VERGE_RULES[s.colors].requires) for s, _ in sources
                            if s.kind == "verge" and VERGE_RULES[s.colors].secondary in colored))
    possible = set().union(*(set(s.types) for s, _ in sources))
    types = tuple(c for c in COLORS if c in relevant & possible)
    required = Counter(colored)
    colors = tuple(required)
    groups = [tuple(c for i, c in enumerate(colors) if mask & (1 << i))
              for mask in range(1, 1 << len(colors))]
    caps = tuple(sum(required[c] for c in group) for group in groups)
    payable = [0] * (max_drawn + 1)
    for target in range(1 << len(types)):
        supplies = Counter()
        reachable = 0
        for (source, count), rate in zip(sources, rates):
            type_mask = sum(1 << i for i, c in enumerate(types) if c in source.types)
            if type_mask & ~target:
                continue  # This scenario draws zero of this source.
            reachable |= type_mask
            options = source.primary_colors
            if source.kind == "verge":
                rule = VERGE_RULES[source.colors]
                if any(target & (1 << i) for i, c in enumerate(types) if c in rule.requires):
                    options += rule.secondary
            supply = tuple(int(any(c in options for c in group)) for group in groups)
            supplies[supply, type_mask, rate] += count
        if reachable != target:
            continue
        states = {(0, 0, (0,) * len(caps), 0): 1}
        denominator = 1
        for (supply, type_mask, rate), count in supplies.items():
            next_states = defaultdict(int)
            p, d = rate.numerator, rate.denominator
            denominator *= d**count
            outcomes = []
            for take in range(min(count, max_drawn) + 1):
                distribution = defaultdict(int)
                for available in range(take + 1):
                    mass = (comb(count, take) * comb(take, available) * p**available
                            * (d-p)**(take-available) * d**(count-take))
                    if mass:
                        distribution[min(total, available)] += mass
                outcomes.append(tuple(distribution.items()))
            for (drawn, observed, covered, available), weight in states.items():
                for take in range(min(count, max_drawn - drawn) + 1):
                    seen_types = observed | type_mask if take else observed
                    for extra, mass in outcomes[take]:
                        updated = tuple(min(cap, have + extra * adds)
                                        for cap, have, adds in zip(caps, covered, supply))
                        next_states[drawn + take, seen_types, updated, min(total, available + extra)] += weight * mass
            states = next_states
        for (drawn, observed, covered, available), weight in states.items():
            if drawn >= generic + len(colored) and observed == target and covered == caps and available == total:
                payable[drawn] += Fraction(weight, denominator)
    return tuple(payable)


def evaluate(mana_base: Mapping[ManaSource, int], spells: Sequence[SpellCost | Spell], *, turns: int = 7,
             position: Literal["both", "play", "draw"] = "both", opening_hand_size: int = 7,
             town_penalty: float = 0, shock_penalty: float = 0) -> OpportunityResult:
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
    town_penalty = _weight(town_penalty, "Town penalty")
    shock_penalty = _weight(shock_penalty, "Shock penalty")

    sources = Counter()
    penalties = []
    for source, count in mana_base.items():
        if not isinstance(source, ManaSource):
            raise ValueError("Mana base keys must be ManaSource inputs")
        _count(count, "Land count")
        if count:
            sources[source] += count
        penalties.append(count * {"basic": 0, "verge": 0, "shock": shock_penalty,
                                  "town": town_penalty, "cavern": 0, "fast": 0, "slow": 0, "tapped": 0}[source.kind])
    nonlands, counts, weighted_counts = spell_components(spells)
    deck_size = sum(sources.values()) + nonlands
    if not deck_size:
        raise ValueError("Deck must contain at least one card")
    positions = ("play", "draw") if position == "both" else (position,)
    max_seen = min(deck_size, max(opening_hand_size + turns - (side == "play") for side in positions))
    max_lands = min(sum(sources.values()), max(0, max_seen - 1))
    source_key = tuple(sorted(sources.items(), key=lambda item: (item[0].kind, item[0].colors, item[0].types)))
    conditional = any(s.kind == "verge" for s in sources)
    plain_sources = Counter()
    for source, count in sources.items():
        plain_sources[source.colors] += count
    rows = []
    for cost, copies in counts.items():
        generic, colored = _parse_cost(cost)
        total = generic + len(colored)
        weights = ()
        if copies and total <= turns:
            if conditional:
                weights = _verge_land_weights(source_key, generic, colored, max_lands)
            else:
                weights = _payable_land_weights(tuple(sorted(plain_sources.items())), generic, colored, max_lands)
        weighted_copies = float(weighted_counts[cost])
        for turn in range(1, turns + 1):
            rates = tuple(land_availability(source.kind, turn) for source, _ in source_key)
            turn_weights = weights
            if copies and total and total <= turn and any(rate != 1 for rate in rates):
                turn_weights = _available_land_weights(source_key, generic, colored, max_lands, rates)
            for side in positions:
                seen = min(deck_size, opening_hand_size + turn - (side == "play"))
                # Mark one physical spell: choose the remaining nonlands and
                # lands around it. Multiplying by copies counts every backup.
                numerator = sum(land_weight * comb(nonlands - 1, seen - k - 1)
                                for k, land_weight in enumerate(turn_weights)
                                if 0 <= seen - k - 1 <= nonlands - 1) if total <= turn else 0
                per_copy = Fraction(numerator, comb(deck_size, seen))
                rows.append(Opportunity(cost, turn, side, copies * per_copy, weighted_copies * float(per_copy)))

    raw_score = fsum(row.weighted_contribution for row in rows) / (turns * len(positions))
    penalty = fsum(penalties)
    return OpportunityResult(tuple(rows), raw_score, penalty, raw_score - penalty)
