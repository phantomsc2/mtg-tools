"""Spell costs, casting modes, and normalized physical-copy profiles."""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
from numbers import Real

from mtg_tools.mana.lands import COLORS


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
