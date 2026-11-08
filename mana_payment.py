"""Payment constraints and model projections shared by both evaluation backends.

For one-mana sources, Hall coverage plus total mana is necessary and sufficient.
All increments come from realized source outcomes, including availability failures.
"""

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from math import lcm

from mana_model import CompiledManaModel, type_mask

Supply = tuple[int, ...]
Distribution = tuple[tuple[Supply, Fraction], ...]


def requirements(generic: int, colored: str) -> tuple[tuple[str, ...], Supply]:
    required = Counter(colored)
    groups = tuple("".join(group) for size in range(1, len(required) + 1)
                   for group in combinations(required, size))
    return groups, (generic + len(colored), *(sum(required[c] for c in group) for group in groups))


@dataclass(frozen=True)
class PaymentScenario:
    type_masks: tuple[int, ...]
    contexts: tuple[int, ...]
    distributions: tuple[Distribution, ...]


@lru_cache(maxsize=128)
def payment_scenarios(model: CompiledManaModel, generic: int, colored: str
                      ) -> tuple[tuple[int | None, tuple[PaymentScenario, ...]], ...]:
    groups, caps = requirements(generic, colored)
    rows = []
    for limit, table in model.turns:
        projected = []
        for context in table:
            sources = []
            for outcomes in context:
                merged = defaultdict(Fraction)
                for outcome in outcomes:
                    colors = "".join(outcome.options)
                    supply = (int(bool(colors)), *(int(bool(set(colors) & set(group))) for group in groups))
                    merged[tuple(min(cap, n) for cap, n in zip(caps, supply))] += outcome.probability
                sources.append(tuple(sorted(merged.items())))
            projected.append(tuple(sources))
        # Retain only context bits needed to distinguish production distributions.
        mask = next(mask for size in range(6) for bits in combinations(range(5), size)
                    for mask in (sum(1 << bit for bit in bits),)
                    if len({(context & mask, outcome) for context, outcome in zip(model.contexts, projected)})
                    == len({context & mask for context in model.contexts}))
        partitions = defaultdict(set)
        for context, outcome in zip(model.contexts, projected):
            partitions[outcome].add(context & mask)
        rows.append((limit, tuple(PaymentScenario(
            tuple(type_mask(source.types) & mask for source in model.sources), tuple(sorted(contexts)), outcomes)
            for outcomes, contexts in partitions.items())))
    return tuple(rows)


def probability_counter(distributions: tuple[Distribution, ...]
                        ) -> tuple[Callable[[tuple[int, ...], Supply], int], int]:
    """Return a memoized success mass and its common per-source denominator."""
    scale = lcm(*(p.denominator for dist in distributions for _, p in dist))
    outcomes = tuple(tuple((supply, int(p * scale)) for supply, p in dist) for dist in distributions)

    @lru_cache(maxsize=None)
    def mass(counts: tuple[int, ...], needs: Supply) -> int:
        if not any(needs):
            return scale**sum(counts)
        if not any(counts) or needs[0] > sum(counts):
            return 0
        axis = next(i for i, n in enumerate(counts) if n)
        previous = tuple(n - (i == axis) for i, n in enumerate(counts))
        return sum(p * mass(previous, tuple(max(0, need - n) for need, n in zip(needs, supply)))
                   for supply, p in outcomes[axis])

    return mass, scale
