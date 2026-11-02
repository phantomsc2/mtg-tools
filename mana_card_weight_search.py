"""Exact sensitivity to Awaken the Honored Dead's normalized per-copy weight."""
import json
from fractions import Fraction
from math import lcm
from pathlib import Path

import click

from mana_analysis import ROOT
from mana_basic_search import NAMES, evaluate_pool

CARD = "Awaken the Honored Dead"


def first_transition(lines: list[tuple[int, int]], start: Fraction = Fraction(1)
                     ) -> tuple[int, int, Fraction, Fraction | None]:
    """First change of the upper envelope a+b*w after start; compare exactly."""
    baseline = max(range(len(lines)), key=lambda i: lines[i][0]+lines[i][1]*start)
    a, b = lines[baseline]
    roots = [(Fraction(a-aa, bb-b), i) for i, (aa, bb) in enumerate(lines) if bb > b]
    roots = [(root, i) for root, i in roots if root >= start]
    if not roots:
        raise ValueError("Increasing this card's weight never changes the optimum")
    threshold = min(root for root, _ in roots)
    successor = max((i for root, i in roots if root == threshold), key=lambda i: lines[i][1])
    a, b = lines[successor]
    upper = min((Fraction(a-aa, bb-b) for aa, bb in lines
                 if bb > b and Fraction(a-aa, bb-b) > threshold), default=None)
    return baseline, successor, threshold, upper


def nearby_weight(lower: Fraction, upper: Fraction | None) -> Fraction:
    denominator = 100
    while True:
        candidate = Fraction((lower*denominator).__floor__()+1, denominator)
        if upper is None or candidate < upper:
            return candidate
        denominator *= 10


def search(penalty: Fraction, requested_weight: Fraction | None, output: Path) -> None:
    bases, successes, common, components = evaluate_pool()
    (play, dp), (draw, dd) = components[(3, "BGU", False, 3)]
    scale = lcm(common, 2*dp, 2*dd, penalty.denominator)
    normal = [successes[b]*(scale//common) for b in bases]
    awaken = [int(p)*(scale//(2*dp))+int(d)*(scale//(2*dd)) for p, d in zip(play, draw)]
    penalized = [sum(base[i] for i in (1, 2, 3, 7)) for base in bases]
    costs = [penalty.numerator*(scale//penalty.denominator)*k for k in penalized]
    # S(w) = [34*S(1) + 3*(w-1)*P(Awaken)] / (31+3*w).
    # Multiplying S(w)-lambda*K by its positive common denominator yields a line.
    lines = [(34*s-3*p-31*c, 3*p-3*c) for s, p, c in zip(normal, awaken, costs)]
    baseline, successor, threshold, upper = first_transition(lines)
    weight = nearby_weight(threshold, upper) if requested_weight is None else requested_weight
    winner = max(range(len(bases)), key=lambda i: lines[i][0]+lines[i][1]*weight)
    if requested_weight is None:
        assert winner == successor and winner != baseline

    def result(i: int, factor: Fraction) -> dict:
        value = Fraction(34*normal[i]+3*(factor-1)*awaken[i], scale*(31+3*factor))
        loss = 1-value+penalty*penalized[i]
        return dict(composition=dict(zip(NAMES, bases[i])), weight=str(factor),
                    ordinary_success=str(Fraction(normal[i], scale)), weighted_success=str(value),
                    regularized_loss=str(loss), awaken_play=str(Fraction(int(play[i]), dp)),
                    awaken_draw=str(Fraction(int(draw[i]), dd)), awaken_average=str(Fraction(awaken[i], scale)),
                    penalized_lands=penalized[i])

    before, after = result(baseline, Fraction(1)), result(winner, weight)
    # Compare both compositions under the selected weighting, not different objectives.
    before_selected = result(baseline, weight)
    data = dict(card=CARD, penalty=str(penalty), candidates=len(bases), threshold=str(threshold),
                first_successor_until=str(upper) if upper is not None else None,
                selected_weight=str(weight), before=before, before_at_selected_weight=before_selected, after=after)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    text = ["# Awaken importance sensitivity", "",
            "Same 59,109-base bounded pool: 26 lands, 1–2 Swamps, 0–1 Island, 0–1 Forest,",
            "four-copy nonbasics. No Passage. Same conditional direct metric and equal play/draw weighting.", "",
            "Multiply each Awaken copy's importance by w; other cards retain weight one. Renormalize",
            "by total weighted copies, 31+3w. Modes stay uniform within a card. Minimize",
            f"1 - weighted_success + {penalty} * (shocks + Towns).", "",
            f"First change above w=1: **w={float(threshold):.12f}** (tie at the exact boundary).",
            f"Selected weight: **{float(weight):g}**, an increase of {float(weight-1)*100:.4f}%.",
            f"First successor remains optimal until {float(upper):.12f}." if upper is not None else
            "First successor has no upper transition.", "", "| Land | Before | After |", "|---|---:|---:|"]
    text.extend(f"| {name} | {bases[baseline][i]} | {bases[winner][i]} |" for i, name in enumerate(NAMES)
                if bases[baseline][i] or bases[winner][i])
    text.extend(["", "| Metric | Before | After |", "|---|---:|---:|"])
    for label, key in (("Awaken on play", "awaken_play"), ("Awaken on draw", "awaken_draw"),
                       ("Awaken average", "awaken_average"), ("Ordinary color success", "ordinary_success")):
        text.append(f"| {label} | {float(Fraction(before[key])):.6%} | {float(Fraction(after[key])):.6%} |")
    for label, key in (("Weighted color success at selected w", "weighted_success"),
                       ("Regularized loss at selected w", "regularized_loss")):
        text.append(f"| {label} | {float(Fraction(before_selected[key])):.6%} | "
                    f"{float(Fraction(after[key])):.6%} |")
    text.extend(["", "All probability, crossing and ranking calculations use exact integer/rational arithmetic.",
                 "JSON retains exact fractions. The denominator 31+3w is common across all bases, so",
                 "the first optimum change is an exact crossing of linear functions after clearing it.",
                 "This is exhaustive within the bounded pool, not unrestricted-basic optimization.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")
    print(json.dumps(data, indent=2), flush=True)


def load_config(context: click.Context, parameter: click.Parameter, path: Path | None) -> None:
    if path is None or context.resilient_parsing:
        return
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict) or set(values)-{"weight", "penalty", "output"}:
            raise ValueError("Expected an object containing weight, penalty or output defaults")
    except (OSError, ValueError) as error:
        raise click.BadParameter(str(error), param_hint="config") from error
    context.default_map = {**(context.default_map or {}), **values}


@click.command()
@click.option("--config", type=click.Path(exists=True, path_type=Path), is_eager=True,
              expose_value=False, callback=load_config, help="JSON defaults; CLI options take precedence.")
@click.option("--penalty", default="0.0032", help="Exact normalized shock/Town penalty.")
@click.option("--weight", default=None, help="Awaken multiplier; omit to select just above the first transition.")
@click.option("--output", type=click.Path(path_type=Path), default=ROOT / "reports/awaken-weight-search")
def main(penalty: str, weight: str | None, output: Path) -> None:
    try:
        coefficient = Fraction(penalty)
        factor = None if weight is None else Fraction(weight)
        if coefficient < 0 or (factor is not None and factor < 1):
            raise ValueError("Penalty must be nonnegative and weight at least one")
    except (ValueError, ZeroDivisionError) as error:
        raise click.BadParameter(str(error)) from error
    search(coefficient, factor, output)


if __name__ == "__main__":
    main()
