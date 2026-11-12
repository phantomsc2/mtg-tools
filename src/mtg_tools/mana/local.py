"""Budgeted local optimization over legal mana-base neighborhoods."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter

from mtg_tools.mana.evaluation import LocalManaEvaluator, LocalNeighborhood, RankedBase
from mtg_tools.mana.lands import ManaSource


@dataclass(frozen=True)
class LocalSearchResult:
    baseline: RankedBase
    best: RankedBase
    moves: tuple[RankedBase, ...]
    evaluations: int
    seconds: float
    stopped: str


def value_and_swap_deltas(evaluator: LocalManaEvaluator, base: Mapping[ManaSource, int], *, evaluation_budget: int | None = None,
                          max_replacements: int = 1,
                          _visited: set[tuple[int, ...]] | None = None) -> LocalNeighborhood:
    """Score a one- or two-land neighborhood in canonical order.

    Budget counts distinct bases considered, including cached ones and the
    reference. The search shares its visited set between neighborhoods.
    """
    if evaluation_budget is not None and (type(evaluation_budget) is not int or evaluation_budget < 1):
        raise ValueError("Evaluation budget must be a positive integer or None")
    visited = set() if _visited is None else _visited
    counts = evaluator.space.counts(base)
    candidates = evaluator.space.neighbor_counts(base, max_replacements=max_replacements)
    current = evaluator.value(base)
    visited.add(counts)
    neighbors = []
    complete = True
    for candidate in candidates:
        if candidate not in visited and evaluation_budget is not None and len(visited) >= evaluation_budget:
            complete = False
            break
        value = evaluator.value(dict(zip(evaluator.space.sources, candidate)))
        visited.add(candidate)
        neighbors.append(evaluator._relative(current, value))
    return LocalNeighborhood(current, tuple(neighbors), complete)


def local_search(evaluator: LocalManaEvaluator, initial: Mapping[ManaSource, int], *,
                 evaluation_budget: int = 500,
                 max_replacements: int = 2,
                 progress: Callable[[int, RankedBase], None] | None = None) -> LocalSearchResult:
    """One-land descent, followed by a two-land completion check by default.

    An improving completion move resumes one-land descent before checking again.
    Set max_replacements=1 for the cheaper one-land-only search. A certificate
    requires a complete final neighborhood; budget exhaustion never certifies it.

    evaluations counts unique bases visited this run (cache hits included).
    A partial final neighborhood returns the best evaluated base, without a
    local-optimality claim. Move deltas are relative to the preceding base.
    """
    if type(evaluation_budget) is not int or evaluation_budget < 1:
        raise ValueError("Evaluation budget must be a positive integer")
    if type(max_replacements) is not int or max_replacements not in (1, 2):
        raise ValueError("Maximum replacements must be 1 or 2")
    started = perf_counter()
    baseline = evaluator.value(initial)
    current = baseline
    visited: set[tuple[int, ...]] = set()
    moves = []
    radius = 1
    while True:
        neighborhood = value_and_swap_deltas(evaluator,
            dict(zip(evaluator.space.sources, current.counts)), evaluation_budget=evaluation_budget,
            max_replacements=radius, _visited=visited)
        best = min((current, *neighborhood.neighbors), key=lambda row: (-row.score, row.counts))
        improved = best.score > current.score
        if improved:
            moves.append(best)
            current = best
        if progress is not None:
            progress(len(visited), current)
        if not neighborhood.complete:
            stopped = "evaluation budget"
            break
        if improved:
            radius = 1
        elif radius < max_replacements:
            radius = max_replacements
        else:
            stopped = "two-land local optimum" if radius == 2 else "one-land local optimum"
            break
    return LocalSearchResult(baseline, evaluator._relative(baseline, current), tuple(moves),
                             len(visited), perf_counter() - started, stopped)
