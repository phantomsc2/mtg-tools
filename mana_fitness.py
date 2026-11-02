"""Normalized copy/mode/play-draw weights for the direct mana fitness."""
from collections import Counter
from collections.abc import Mapping, Sequence
from fractions import Fraction

from mana_analysis import LANDS, Mode


def mode_weights(deck: Mapping[str, int], modes: Sequence[Mode],
                 card_weights: Mapping[str, Fraction] | None = None) -> tuple[tuple[Mode, Fraction], ...]:
    """Per-position weights: sum across modes and both play/draw equals one.

    A card's weight multiplies its physical copy count. Modes remain uniform
    within each card, and play/draw retain equal weights.
    """
    weights = {name: Fraction(value) for name, value in (card_weights or {}).items()}
    counts = Counter(mode.card for mode in modes)
    if set(deck)-set(LANDS) != set(counts):
        raise ValueError("Casting modes must cover exactly the deck's nonlands")
    if set(weights)-set(counts) or any(value < 0 for value in weights.values()):
        raise ValueError("Card weights must be nonnegative and refer to nonlands in the deck")
    total = sum((deck[name]*weights.get(name, Fraction(1)) for name in counts), Fraction())
    if not total:
        raise ValueError("At least one nonland must have positive weight")
    return tuple((mode, deck[mode.card]*weights.get(mode.card, Fraction(1))/(2*counts[mode.card]*total))
                 for mode in modes)
