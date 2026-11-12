"""Explicit heuristic mana production and land availability policies."""

from collections.abc import Callable
from fractions import Fraction

from mtg_tools.mana.lands import LAND_KINDS, VERGE_RULES, ManaSource
from mtg_tools.mana.model import ManaContext, ManaModel, ManaOutcome, _probability


def land_availability(kind: str, turn: int) -> Fraction:
    """Probability of availability after a uniform play turn in 1..turn.

    Assume one land drop each turn. Earlier drops have untapped; only entry on
    the evaluation turn can fail. Life is always paid for shocks.
    """
    if kind not in LAND_KINDS or type(turn) is not int or turn < 1:
        raise ValueError("A known land kind and positive integer turn are required")
    tapped_now = (kind in ("tapped", "tri", "typed_tapped") or kind in ("town", "fast") and turn > 3
                  or kind == "slow" and turn < 3)
    return Fraction(turn - int(tapped_now), turn)


def heuristic_availability(source: ManaSource, turn: int) -> Fraction:
    return land_availability(source.kind, turn)


def turn_source_limit(turn: int) -> int:
    return turn


def heuristic_mana_model(*, availability: Callable[[ManaSource, int], Fraction] = heuristic_availability,
                         source_limit: Callable[[int], int | None] = turn_source_limit) -> ManaModel:
    """Opt into uniform-play-turn availability and enabling types anywhere seen.

    Cavern is unrestricted rainbow mana, shocks always pay life, and no land-drop
    sequence is simulated. Availability may vary independently by source and turn.
    """
    def outcomes(source: ManaSource, context: ManaContext) -> tuple[ManaOutcome, ...]:
        colors = source.colors
        if source.kind == "verge":
            rule = VERGE_RULES[source.colors]
            colors = rule.primary + (rule.secondary if set(context.seen_types) & set(rule.requires) else "")
        rate = _probability(availability(source, context.turn))
        return (ManaOutcome(rate, tuple(colors)), ManaOutcome(1 - rate, ("",)))

    return ManaModel(outcomes, source_limit)
