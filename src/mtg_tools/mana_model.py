"""Explicit production policies, compiled before evaluating draw distributions.

Callbacks must be pure. Outcomes of different physical sources are independent
conditional on the context. An outcome offers alternative bundles, not random
color choices. Only empty and single-mana bundles are supported for now.
"""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from functools import cached_property

from mtg_tools.mana_lands import COLORS, ManaSource, VERGE_RULES, land_availability

MODEL_VERSION = 1


def _probability(value: Fraction) -> Fraction:
    try:
        probability = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise ValueError("Outcome probabilities must be finite and between zero and one") from None
    if not 0 <= probability <= 1:
        raise ValueError("Outcome probabilities must be finite and between zero and one")
    return probability


@dataclass(frozen=True)
class ManaContext:
    turn: int
    seen_types: str


@dataclass(frozen=True)
class ManaOutcome:
    probability: Fraction
    options: tuple[str, ...]

    def __post_init__(self) -> None:
        probability = _probability(self.probability)
        options = tuple(self.options)
        if not options or any(not isinstance(bundle, str) or len(bundle) > 1
                              or set(bundle) - set(COLORS) for bundle in options):
            raise ValueError("Supply alternative empty or single-mana WUBRG bundles")
        # Producing nothing is always allowed; it adds no choice beside real mana.
        options = tuple(sorted(set(options) - {""})) or ("",)
        object.__setattr__(self, "probability", probability)
        object.__setattr__(self, "options", options)


def _canonical(outcomes: tuple[ManaOutcome, ...]) -> tuple[ManaOutcome, ...]:
    merged = defaultdict(Fraction)
    for outcome in outcomes:
        if not isinstance(outcome, ManaOutcome):
            raise ValueError("Models must return ManaOutcome entries")
        merged[outcome.options] += outcome.probability
    if sum(merged.values()) != 1:
        raise ValueError("Source outcome probabilities must sum to one")
    return tuple(ManaOutcome(p, options) for options, p in sorted(merged.items()) if p)


def type_mask(types: str) -> int:
    return sum(1 << i for i, c in enumerate(COLORS) if c in types)


@dataclass(frozen=True)
class CompiledManaModel:
    sources: tuple[ManaSource, ...]
    contexts: tuple[int, ...]
    # Per turn: source limit, then outcome distributions indexed by context/source.
    turns: tuple[tuple[int | None, tuple[tuple[tuple[ManaOutcome, ...], ...], ...]], ...]

    @cached_property
    def _hash(self) -> int:
        return hash(self.signature)

    def __hash__(self) -> int:
        return self._hash

    @property
    def signature(self) -> tuple:
        """Serializable cache identity; deliberately excludes callback identities."""
        return MODEL_VERSION, self.sources, self.contexts, self.turns

    def compile(self, sources: tuple[ManaSource, ...], turns: int) -> "CompiledManaModel":
        if sources != self.sources or turns != len(self.turns):
            raise ValueError("Compiled model source pool and turn horizon must match")
        return self


@dataclass(frozen=True)
class ManaModel:
    outcomes: Callable[[ManaSource, ManaContext], tuple[ManaOutcome, ...]]
    source_limit: Callable[[int], int | None]

    def compile(self, sources: tuple[ManaSource, ...], turns: int) -> CompiledManaModel:
        if type(turns) is not int or turns < 1:
            raise ValueError("Model compilation requires a positive integer horizon")
        contexts = {0}
        for source in sources:
            contexts |= {mask | type_mask(source.types) for mask in contexts}
        contexts = tuple(sorted(contexts))
        rows = []
        for turn in range(1, turns + 1):
            limit = self.source_limit(turn)
            if limit is not None and (type(limit) is not int or limit < 0):
                raise ValueError("Source limits must be nonnegative integers or None")
            table = []
            for mask in contexts:
                context = ManaContext(turn, "".join(c for i, c in enumerate(COLORS) if mask & (1 << i)))
                table.append(tuple(_canonical(self.outcomes(source, context)) for source in sources))
            rows.append((limit, tuple(table)))
        return CompiledManaModel(sources, contexts, tuple(rows))


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
