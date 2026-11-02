"""Finite-deck expectations for arbitrary pure functions of unordered hands."""

from collections import Counter
from collections.abc import Callable, Hashable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from math import comb, fsum, isfinite, prod
from typing import TypeVar

TCard = TypeVar("TCard", bound=Hashable)


def hand_weights(deck: Mapping[TCard, int], hand_size: int = 7) -> Iterator[tuple[Counter[TCard], int]]:
    """Unnormalized integer weights; their sum is comb(deck size, hand size)."""
    cards, counts = tuple(deck), tuple(deck.values())
    if any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("Deck counts must be nonnegative integers")
    if type(hand_size) is not int or not 0 <= hand_size <= sum(counts):
        raise ValueError("Hand size must be an integer between zero and deck size")
    for hand in compositions(counts, hand_size):
        yield Counter({c: k for c, k in zip(cards, hand) if k}), prod(comb(n, k) for n, k in zip(counts, hand))


@dataclass(frozen=True)
class Card:
    name: str
    mana_value: int = 0
    roles: frozenset[str] = frozenset()


def compositions(capacities: Sequence[int], total: int) -> Iterator[tuple[int, ...]]:
    """Enumerate bounded integer count vectors summing to total."""
    if not capacities:
        if total == 0:
            yield ()
        return
    low = max(0, total - sum(capacities[1:]))
    for count in range(low, min(capacities[0], total) + 1):
        for rest in compositions(capacities[1:], total - count):
            yield (count, *rest)


def hand_distribution(deck: Mapping[TCard, int], hand_size: int = 7) -> Iterator[tuple[Counter[TCard], float]]:
    """Enumerate feasible hands and their multivariate hypergeometric probabilities."""
    cards, counts = tuple(deck), tuple(deck.values())
    if any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("Deck counts must be nonnegative integers")
    if type(hand_size) is not int or not 0 <= hand_size <= sum(counts):
        raise ValueError("Hand size must be an integer between zero and deck size")
    denominator = comb(sum(counts), hand_size)
    for hand in compositions(counts, hand_size):
        probability = prod(comb(n, k) for n, k in zip(counts, hand)) / denominator
        yield Counter({card: k for card, k in zip(cards, hand) if k}), probability


def expected_score(
    deck: Mapping[TCard, int], score_hand: Callable[[Counter[TCard]], float], hand_size: int = 7
) -> float:
    """Exhaustive expectation, with floating-point arithmetic (no sampling)."""
    def terms() -> Iterator[float]:
        for hand, probability in hand_distribution(deck, hand_size):
            score = float(score_hand(hand))
            if not isfinite(score):
                raise ValueError("Hand scores must be finite")
            yield probability * score

    return fsum(terms())
