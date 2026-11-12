"""Normalized uniform or exponential turn weights shared by all evaluators."""
from dataclasses import dataclass
from fractions import Fraction
from math import floor, isfinite, log2
from numbers import Real


@dataclass(frozen=True)
class TurnTiming:
    weights: tuple[Fraction, ...]
    half_life: float | None = None
    tail_tolerance: float | None = None
    omitted_mass: float = 0.0

    @property
    def horizon(self):
        return len(self.weights)

    @property
    def signature(self):
        return ('turn-timing-v1', self.half_life, self.tail_tolerance, self.weights)


def resolve_timing(*, turns: int | None = None, half_life: Real | None = None,
                   tail_tolerance: Real = 0.05) -> TurnTiming:
    """Choose minimal H with 2**(-H/h) < tolerance; quantize raw weights to 1e-9."""
    if (isinstance(tail_tolerance, bool) or not isinstance(tail_tolerance, Real)
            or not isfinite(tail_tolerance) or not 0 < tail_tolerance < 1):
        raise ValueError('Tail tolerance must be finite and strictly between zero and one')
    if half_life is None:
        turns = 7 if turns is None else turns
        if type(turns) is not int or turns < 1:
            raise ValueError('Turn horizon must be a positive integer')
        return TurnTiming((Fraction(1, turns),) * turns)
    if turns is not None:
        raise ValueError('Supply turns or half_life, not both')
    if (isinstance(half_life, bool) or not isinstance(half_life, Real)
            or not isfinite(half_life) or half_life <= 0):
        raise ValueError('Half life must be finite and positive')
    h, tolerance = float(half_life), float(tail_tolerance)
    boundary = h * -log2(tolerance)
    if not isfinite(boundary):
        raise ValueError('Derived turn horizon is not finite')
    horizon = max(1, floor(boundary) + 1)
    # Comparing exponents avoids underflow when the half-life is very small.
    while -horizon / h >= log2(tolerance):
        horizon += 1
    while horizon > 1 and -(horizon - 1) / h < log2(tolerance):
        horizon -= 1
    units = tuple(round(10**9 * 2**(-n / h)) for n in range(horizon))
    total = sum(units)
    return TurnTiming(tuple(Fraction(n, total) for n in units), h, tolerance, 2**(-horizon / h))
