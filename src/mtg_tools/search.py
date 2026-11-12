"""Integer deck search with a shared exact objective and evaluation budget."""

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import exp, floor, isfinite
from random import Random
from time import perf_counter
from typing import Generic

from mtg_tools.hands import TCard, expected_score


@dataclass(frozen=True)
class DeckSpace(Generic[TCard]):
    cards: tuple[TCard, ...]
    minimum: tuple[int, ...]
    maximum: tuple[int, ...]
    size: int = 60

    def __post_init__(self) -> None:
        if not self.cards or len(set(self.cards)) != len(self.cards):
            raise ValueError("Card types must be nonempty and unique")
        if len(self.cards) != len(self.minimum) or len(self.cards) != len(self.maximum):
            raise ValueError("One lower and upper bound is required per type")
        if type(self.size) is not int or any(
            type(lo) is not int or type(hi) is not int or not 0 <= lo <= hi
            for lo, hi in zip(self.minimum, self.maximum)
        ) or not sum(self.minimum) <= self.size <= sum(self.maximum):
            raise ValueError("Infeasible integer deck bounds")

    def validate(self, counts: Sequence[int]) -> tuple[int, ...]:
        counts = tuple(counts)
        if len(counts) != len(self.cards) or sum(counts) != self.size or any(
            type(n) is not int or not lo <= n <= hi
            for n, lo, hi in zip(counts, self.minimum, self.maximum)
        ):
            raise ValueError("Deck is outside its count bounds")
        return counts

    def decode(self, logits: Sequence[float]) -> tuple[int, ...]:
        """Minimums plus capped proportional quotas, then largest-remainder rounding."""
        if len(logits) != len(self.cards) or not all(isfinite(x) for x in logits):
            raise ValueError("One finite preference is required per type")
        capacities = [hi - lo for lo, hi in zip(self.minimum, self.maximum)]
        quotas = [0.0] * len(self.cards)
        remaining = self.size - sum(self.minimum)
        active = [i for i, cap in enumerate(capacities) if cap]
        while remaining and active:
            peak = max(logits[i] for i in active)
            weights = {i: exp(logits[i] - peak) for i in active}
            total = sum(weights.values())
            shares = {i: remaining * weights[i] / total for i in active}
            capped = [i for i in active if shares[i] >= capacities[i]]
            if not capped:
                for i in active:
                    quotas[i] = shares[i]
                break
            for i in capped:
                quotas[i] = capacities[i]
                remaining -= capacities[i]
                active.remove(i)
        allocated = [floor(q) for q in quotas]
        residual = self.size - sum(self.minimum) - sum(allocated)
        order = sorted(
            (i for i in range(len(quotas)) if allocated[i] < capacities[i]),
            key=lambda i: (-(quotas[i] - allocated[i]), i),
        )
        for i in order[:residual]:
            allocated[i] += 1
        return self.validate([lo + n for lo, n in zip(self.minimum, allocated)])


class BudgetExhausted(Exception):
    pass


class Objective(Generic[TCard]):
    def __init__(self, space: DeckSpace[TCard], score_hand: Callable[[Counter[TCard]], float],
                 budget: int = 200, hand_size: int = 7) -> None:
        if budget < 1 or not 0 <= hand_size <= space.size:
            raise ValueError("Positive budget and feasible hand size required")
        self.space, self.score_hand = space, score_hand
        self.budget, self.hand_size = budget, hand_size
        self.cache: dict[tuple[int, ...], float] = {}

    def __call__(self, counts: Sequence[int]) -> float:
        key = self.space.validate(counts)
        if key not in self.cache:
            if len(self.cache) >= self.budget:
                raise BudgetExhausted
            self.cache[key] = expected_score(dict(zip(self.space.cards, key)), self.score_hand, self.hand_size)
        return self.cache[key]


@dataclass(frozen=True)
class SearchResult:
    counts: tuple[int, ...]
    score: float
    evaluations: int
    proposals: int
    seconds: float
    stopped: str


def optimize(objective: Objective, initial: Sequence[int], seed: int = 0,
             max_proposals: int | None = None) -> SearchResult:
    """Search a fresh objective; count the initial deck against the evaluation budget.

    A proposal cap prevents endless duplicate proposals on plateaus or exhausted spaces.
    Discrete search uses best-improvement transfers, restarting at local optima.
    """
    if objective.cache:
        raise ValueError("Use a fresh objective")
    start = perf_counter()
    current = objective.space.validate(initial)
    objective(current)
    rng = Random(seed)
    proposals = 1
    limit = max_proposals if max_proposals is not None else 20 * objective.budget
    stopped = "proposal limit"
    space = objective.space
    try:
        while proposals < limit:
            if len(objective.cache) >= objective.budget:
                stopped = "evaluation budget"
                break
            best, best_score = current, objective(current)
            for i in range(len(current)):
                for j in range(len(current)):
                    if i == j or current[i] <= space.minimum[i] or current[j] >= space.maximum[j]:
                        continue
                    if proposals >= limit:
                        break
                    candidate = list(current)
                    candidate[i] -= 1
                    candidate[j] += 1
                    proposals += 1
                    score = objective(candidate)
                    if score > best_score:
                        best, best_score = tuple(candidate), score
            if best == current and proposals < limit:
                current = space.decode([rng.gauss(0, 1.5) for _ in current])
                proposals += 1
                objective(current)
            else:
                current = best
    except BudgetExhausted:
        stopped = "evaluation budget"
    best = max(objective.cache, key=objective.cache.__getitem__)
    return SearchResult(best, objective.cache[best], len(objective.cache), proposals, perf_counter() - start, stopped)
