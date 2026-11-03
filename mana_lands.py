"""Land definitions and card knowledge shared by construction and evaluation."""

from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from types import MappingProxyType
from typing import Literal

COLORS = "WUBRG"
LAND_KINDS = ("basic", "shock", "verge", "town", "cavern", "fast", "slow", "tapped")


# Explicit legality snapshot, not a live rotation service. See knowledge notes.
STANDARD_AS_OF = "2026-11-03"
_PAIRS = frozenset("".join(pair) for pair in combinations(COLORS, 2))
STANDARD_COLORS = MappingProxyType({
    "basic": frozenset(COLORS),
    "shock": _PAIRS,
    "verge": _PAIRS,
    "town": frozenset((COLORS,)),
    "cavern": frozenset((COLORS,)),
    "fast": frozenset(("WB", "WR", "UR", "UG", "BG")),
    "slow": frozenset(),
    # Abstract tapped duals: a legal untyped representative exists for every pair.
    "tapped": _PAIRS,
})


@dataclass(frozen=True)
class VergeRule:
    name: str
    primary: str
    secondary: str
    requires: str


# Source: published card text, linked in ideas/knowledge/mana-opportunities.md.
VERGE_RULES = MappingProxyType({
    "WU": VergeRule("Floodfarm Verge", "W", "U", "WU"),
    "WB": VergeRule("Bleachbone Verge", "B", "W", "WB"),
    "WR": VergeRule("Sunbillow Verge", "W", "R", "WR"),
    "WG": VergeRule("Hushwood Verge", "G", "W", "WG"),
    "UR": VergeRule("Riverpyre Verge", "R", "U", "UR"),
    "BR": VergeRule("Blazemire Verge", "B", "R", "BR"),
    "RG": VergeRule("Thornspire Verge", "R", "G", "RG"),
    "UB": VergeRule("Gloomlake Verge", "U", "B", "UB"),
    "BG": VergeRule("Wastewood Verge", "G", "B", "BG"),
    "UG": VergeRule("Willowrush Verge", "U", "G", "UG"),
})


@dataclass(frozen=True)
class ManaSource:
    colors: str
    kind: Literal["basic", "shock", "town", "cavern", "verge", "fast", "slow", "tapped"]
    types: str = ""

    def __post_init__(self) -> None:
        sizes = {"basic": 1, "shock": 2, "town": 5, "cavern": 5, "verge": 2, "fast": 2, "slow": 2, "tapped": 2}
        if (self.kind not in sizes or not isinstance(self.colors, str)
                or len(self.colors) != sizes[self.kind] or len(set(self.colors)) != len(self.colors)
                or set(self.colors) - set(COLORS)):
            raise ValueError("Sources require one basic color, two dual colors, or five rainbow colors")
        object.__setattr__(self, "colors", "".join(c for c in COLORS if c in self.colors))
        if (not isinstance(self.types, str) or len(set(self.types)) != len(self.types)
                or set(self.types) - set(self.colors)):
            raise ValueError("Land types must be distinct WUBRG letters belonging to the source's colors")
        types = "".join(c for c in COLORS if c in self.types)
        if self.kind == "basic":
            types = types or self.colors
        if ((self.kind in ("town", "cavern", "verge", "fast", "slow", "tapped") and types)
                or (self.kind == "shock" and types not in ("", self.colors))):
            raise ValueError("Only basics and explicitly typed shocks carry basic land types")
        if self.kind == "verge" and self.colors not in VERGE_RULES:
            raise ValueError(f"No Verge production rule registered for {self.colors}")
        object.__setattr__(self, "types", types)

    @property
    def primary_colors(self) -> str:
        return VERGE_RULES[self.colors].primary if self.kind == "verge" else self.colors


def sources_for_colors(colors: str, families: Iterable[str], *,
                       format: Literal["standard"] | None = None) -> tuple[ManaSource, ...]:
    """Select on-color lands, typed shocks, and explicitly enabled rainbow families."""
    if (not isinstance(colors, str) or not colors or len(set(colors)) != len(colors)
            or set(colors) - set(COLORS)):
        raise ValueError("Select distinct colors from WUBRG")
    if format not in (None, "standard"):
        raise ValueError("Supported formats: standard, or None for an unrestricted pool")
    colors = "".join(c for c in COLORS if c in colors)
    families = set(families)
    if families - set(LAND_KINDS):
        raise ValueError("Unknown land family")
    pairs = tuple("".join(pair) for pair in combinations(colors, 2))
    return tuple(
        ManaSource(pair, kind, pair if kind == "shock" else "")
        for kind in LAND_KINDS if kind in families
        for pair in (tuple(colors) if kind == "basic" else (COLORS,) if kind in ("town", "cavern") else pairs)
        if format is None or pair in STANDARD_COLORS[kind]
    )


def land_availability(kind: str, turn: int) -> Fraction:
    """Probability of availability after a uniform play turn in 1..turn.

    Assume one land drop each turn. Earlier drops have untapped; only entry on
    the evaluation turn can fail. Life is always paid for shocks.
    """
    if kind not in LAND_KINDS or type(turn) is not int or turn < 1:
        raise ValueError("A known land kind and positive integer turn are required")
    tapped_now = (kind == "tapped" or kind in ("town", "fast") and turn > 3
                  or kind == "slow" and turn < 3)
    return Fraction(turn - int(tapped_now), turn)
