"""Feasible mana-base compositions and legal replacement neighborhoods."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from itertools import combinations_with_replacement
from types import MappingProxyType
from typing import Literal

from mtg_tools.hands import compositions
from mtg_tools.mana.lands import ManaSource, sources_for_colors


@dataclass(frozen=True)
class ManaSpace:
    bounds: Mapping[ManaSource, tuple[int, int]]
    land_count: int
    family_bounds: Mapping[str, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def from_colors(cls, land_count: int, colors: str, *,
                    families: Mapping[str, tuple[int, int]],
                    format: Literal["standard"] | None = None,
                    fixed: Mapping[ManaSource, int] | None = None,
                    overrides: Mapping[ManaSource, tuple[int, int]] | None = None,
                    family_bounds: Mapping[str, tuple[int, int]] | None = None) -> "ManaSpace":
        """Derive source bounds from explicit colors and opt-in family bounds.

        families assigns bounds per source; family_bounds limits summed copies
        within each selected family. Exact totals use (n, n). Fixed sources count
        toward these aggregate limits.

        Overrides replace bounds for selected sources. Colors constrain eligible
        lands, not the colors every candidate must produce. Optional format filtering
        uses the centralized catalog's dated legality snapshot. Fixed sources may
        belong to families omitted from the flexible pool; their exact counts
        replace family bounds and are included in land_count, not added to it.
        """
        sources = sources_for_colors(colors, families, format=format)
        for limits in families.values():
            if (len(limits) != 2 or any(type(n) is not int for n in limits)
                    or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Supply a (minimum, maximum) integer pair per generated source")
        bounds = {source: families[source.kind] for source in sources}
        if fixed is not None and overrides is not None and set(fixed).intersection(overrides):
            raise ValueError("A source cannot have both fixed counts and overrides")
        if overrides is not None:
            if set(overrides) - set(bounds):
                raise ValueError("Overrides contain sources outside the selected pool")
            bounds.update(overrides)
        for source, count in (fixed or {}).items():
            if not isinstance(source, ManaSource) or type(count) is not int or count < 0:
                raise ValueError("Fixed lands require ManaSource keys and nonnegative integer counts")
            if source not in sources_for_colors(colors, (source.kind,), format=format):
                raise ValueError("Fixed source is outside the selected colors or format")
            bounds[source] = (count, count)
        return cls(bounds, land_count, {} if family_bounds is None else family_bounds)

    def __post_init__(self) -> None:
        if type(self.land_count) is not int or self.land_count < 0:
            raise ValueError("Land count must be a nonnegative integer")
        for source, limits in self.bounds.items():
            if (not isinstance(source, ManaSource) or len(limits) != 2
                    or any(type(n) is not int for n in limits) or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Supply a (minimum, maximum) integer pair per ManaSource")
        bounds = dict(sorted(self.bounds.items(), key=lambda item: (item[0].kind, item[0].colors, item[0].types)))
        if not sum(lo for lo, _ in bounds.values()) <= self.land_count <= sum(hi for _, hi in bounds.values()):
            raise ValueError("Land count is infeasible within the bounds")
        object.__setattr__(self, "bounds", MappingProxyType({source: tuple(limits) for source, limits in bounds.items()}))
        families = dict(self.family_bounds)
        kinds = {source.kind for source in bounds}
        for kind, limits in families.items():
            if (kind not in kinds or not isinstance(limits, (tuple, list)) or len(limits) != 2
                    or any(type(n) is not int for n in limits) or not 0 <= limits[0] <= limits[1]):
                raise ValueError("Family bounds require selected families and nonnegative integer (minimum, maximum) pairs")
        object.__setattr__(self, "family_bounds", MappingProxyType({kind: tuple(limits) for kind, limits in sorted(families.items())}))
        if any(low > high for _, low, high in self._groups) or not (
                sum(low for _, low, _ in self._groups) <= self.land_count <=
                sum(high for _, _, high in self._groups)):
            raise ValueError("Family bounds are infeasible with source bounds and land count")

    @cached_property
    def _groups(self):
        groups = []
        for kind in sorted({source.kind for source in self.sources}):
            indices = tuple(i for i, source in enumerate(self.sources) if source.kind == kind)
            low = sum(self.bounds[self.sources[i]][0] for i in indices)
            high = sum(self.bounds[self.sources[i]][1] for i in indices)
            minimum, maximum = self.family_bounds.get(kind, (low, high))
            groups.append((indices, max(low, minimum), min(high, maximum)))
        return tuple(groups)

    def _eligible(self, counts):
        return all(low <= sum(counts[i] for i in indices) <= high for indices, low, high in self._groups)


    @property
    def sources(self) -> tuple[ManaSource, ...]:
        return tuple(self.bounds)

    def counts(self, base: Mapping[ManaSource, int]) -> tuple[int, ...]:
        if set(base) - set(self.bounds):
            raise ValueError("Base contains sources outside the pool")
        counts = tuple(base.get(source, 0) for source in self.sources)
        if (any(type(n) is not int or not lo <= n <= hi
                for n, (lo, hi) in zip(counts, self.bounds.values())) or sum(counts) != self.land_count or not self._eligible(counts)):
            raise ValueError("Base is outside the land count, source bounds or family bounds")
        return counts

    def candidate_count(self) -> int:
        """Count legal bases without enumerating or evaluating them."""
        ways = [1] + [0] * self.land_count
        for indices, minimum, maximum in self._groups:
            group = [1] + [0] * self.land_count
            for i in indices:
                low, high = self.bounds[self.sources[i]]
                group = [sum(group[t-n] for n in range(low, min(high, t)+1))
                         for t in range(self.land_count+1)]
            ways = [sum(ways[t-n] * group[n] for n in range(minimum, min(maximum, t)+1))
                    for t in range(self.land_count+1)]
        return ways[self.land_count]

    def exhaustive(self) -> Iterator[tuple[int, ...]]:
        if not self.family_bounds:
            lower = tuple(lo for lo, _ in self.bounds.values())
            capacities = tuple(hi-lo for lo, hi in self.bounds.values())
            for extra in compositions(capacities, self.land_count-sum(lower)):
                yield tuple(lo+n for lo,n in zip(lower,extra))
            return
        groups = self._groups
        counts = [0] * len(self.sources)

        def visit(index, remaining):
            if index == len(groups):
                if remaining == 0:
                    yield tuple(counts)
                return
            indices, minimum, maximum = groups[index]
            tail_low = sum(lo for _,lo,_ in groups[index+1:])
            tail_high = sum(hi for _,_,hi in groups[index+1:])
            lower = tuple(self.bounds[self.sources[i]][0] for i in indices)
            capacities = tuple(self.bounds[self.sources[i]][1]-n for i,n in zip(indices,lower))
            for total in range(max(minimum,remaining-tail_high), min(maximum,remaining-tail_low)+1):
                for extra in compositions(capacities,total-sum(lower)):
                    for i,n,lo in zip(indices,extra,lower):
                        counts[i] = lo+n
                    yield from visit(index+1,remaining-total)
        yield from visit(0,self.land_count)

    def neighbor_counts(self, base: Mapping[ManaSource, int], *,
                        max_replacements: int = 1) -> tuple[tuple[int, ...], ...]:
        """Legal bases within one or two land replacements, deduplicated and sorted.

        Only final compositions must satisfy family totals/maximums. This permits
        coupled moves whose individual transfers would violate an exact total.
        No probabilities or exhaustive composition grid are evaluated here.
        """
        if type(max_replacements) is not int or max_replacements not in (1, 2):
            raise ValueError("Maximum replacements must be 1 or 2")
        counts = self.counts(base)
        limits = tuple(self.bounds.values())
        candidates = set()
        for size in range(1, max_replacements + 1):
            for remove in combinations_with_replacement(range(len(counts)), size):
                residual = list(counts)
                for i in remove:
                    residual[i] -= 1
                if any(n < lo for n, (lo, _) in zip(residual, limits)):
                    continue
                for add in combinations_with_replacement(range(len(counts)), size):
                    candidate = residual.copy()
                    for i in add:
                        candidate[i] += 1
                    if any(n > hi for n, (_, hi) in zip(candidate, limits)):
                        continue
                    candidate = tuple(candidate)
                    if candidate != counts and self._eligible(candidate):
                        candidates.add(candidate)
        return tuple(sorted(candidates))
