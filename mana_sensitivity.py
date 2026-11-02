"""Exact bidirectional optimum crossings for lines a + b*x, x >= 0."""
from dataclasses import dataclass
from fractions import Fraction
from collections.abc import Sequence


@dataclass(frozen=True)
class Crossing:
    status: str
    multiplier: Fraction
    successor: int
    lower: Fraction
    upper: Fraction | None


def lexical_key(base: Sequence[int], names: Sequence[str]) -> tuple[int, ...]:
    return tuple(base[i] for i in sorted(range(len(names)), key=lambda i: names[i]))


def optimal_interval(lines: Sequence[tuple[int, int]], index: int) -> tuple[Fraction, Fraction | None]:
    a, b = lines[index]
    lower, upper = Fraction(0), None
    for aa, bb in lines:
        if b > bb:
            lower = max(lower, Fraction(aa-a, b-bb))
        elif b < bb:
            bound = Fraction(a-aa, bb-b)
            upper = bound if upper is None else min(upper, bound)
        elif a < aa:
            raise ValueError("This line is never optimal")
    if upper is not None and lower > upper:
        raise ValueError("This line is never optimal on the nonnegative domain")
    return lower, upper


def winner_at(lines: Sequence[tuple[int, int]], x: Fraction) -> list[int]:
    values = [a*x.denominator+b*x.numerator for a, b in lines]
    best = max(values)
    return [i for i, value in enumerate(values) if value == best]


def next_crossing(lines: Sequence[tuple[int, int]], bases: Sequence[Sequence[int]], baseline: int,
                  direction: int, names: Sequence[str]) -> Crossing | None:
    """Find the nearest flip around x=1 without probing successive weights.

    At simultaneous intersections choose the extremal slope on the requested
    side, then the fewest replacements, then lexical land-count order.
    """
    if direction not in (-1, 1):
        raise ValueError("Direction must be -1 or +1")
    if baseline not in winner_at(lines, Fraction(1)):
        raise ValueError("Baseline must be optimal at multiplier one")
    a, b = lines[baseline]
    roots = []
    for i, (aa, bb) in enumerate(lines):
        if direction*(bb-b) <= 0:
            continue
        root = Fraction(a-aa, bb-b)
        if (direction == 1 and root >= 1) or (direction == -1 and 0 <= root <= 1):
            roots.append((root, i))
    if not roots:
        return None
    threshold = (min if direction == 1 else max)(root for root, _ in roots)
    tied = [i for root, i in roots if root == threshold]

    def preference(i: int) -> tuple:
        replacements = sum(abs(x-y) for x, y in zip(bases[baseline], bases[i]))//2
        return -direction*lines[i][1], replacements, lexical_key(bases[i], names)

    successor = min(tied, key=preference)
    lower, upper = optimal_interval(lines, successor)
    at_boundary = winner_at(lines, threshold)
    assert baseline in at_boundary and successor in at_boundary
    if direction == -1 and threshold == 0:
        return Crossing("boundary_tie", threshold, successor, lower, upper)
    # Verify the entire first-successor interval, with a point internal to it.
    if direction == 1:
        probe = threshold+1 if upper is None else (threshold+upper)/2
        assert probe > threshold
    else:
        probe = (threshold+lower)/2
        assert 0 <= probe < threshold
    assert successor in winner_at(lines, probe)
    assert baseline in winner_at(lines, (Fraction(1)+threshold)/2)
    status = "already_tied" if threshold == 1 else "crossing"
    return Crossing(status, threshold, successor, lower, upper)


def land_swap(before: Sequence[int], after: Sequence[int], names: Sequence[str]) -> dict:
    if len(before) != len(after) or len(before) != len(names) or sum(before) != sum(after):
        raise ValueError("Land swaps must preserve the land count")
    if any(type(n) is not int or n < 0 for n in (*before, *after)):
        raise ValueError("Land counts must be nonnegative integers")
    out = {name: a-b for name, a, b in zip(names, before, after) if a > b}
    incoming = {name: b-a for name, a, b in zip(names, before, after) if b > a}
    assert sum(out.values()) == sum(incoming.values())
    return {"out": out, "in": incoming, "cards_replaced": sum(out.values())}
