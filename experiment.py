"""Run an illustrative role/curve experiment; customize score_hand freely."""

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import click

from hands import Card, hand_distribution
from search import DeckSpace, Objective, optimize

CARDS = (
    Card("land", roles=frozenset({"land"})),
    Card("early threat", 2, frozenset({"threat"})),
    Card("large threat", 4, frozenset({"threat"})),
    Card("removal", 2, frozenset({"removal"})),
    Card("discard", 1, frozenset({"discard"})),
)


def score_hand(hand: Counter[Card]) -> float:
    """Illustrative preferences, not a calibrated strategic or win-rate model."""
    lands = sum(n for c, n in hand.items() if "land" in c.roles)
    early = sum(n for c, n in hand.items() if "threat" in c.roles and c.mana_value <= 2)
    interaction = sum(n for c, n in hand.items() if c.roles & {"removal", "discard", "counter"})
    return float(2 <= lands <= 4) * (1 + (early > 0) + (interaction > 0))


@click.command()
@click.option("--config", type=click.Path(exists=True, path_type=Path), help="JSON overrides for experiment defaults.")
@click.option("--budget", type=click.IntRange(min=1), default=None)
@click.option("--seed", "seeds", type=int, multiple=True, help="Repeat to compare several search seeds.")
@click.option("--method", type=click.Choice(["both", "discrete", "leitwerk"]), default="both")
def main(config: Path | None, budget: int | None, seeds: tuple[int, ...], method: str) -> None:
    settings = {
        "size": 60, "minimum": [18, 4, 2, 4, 0], "maximum": [30, 24, 12, 20, 12],
        "initial": [24, 12, 6, 12, 6], "budget": 200, "seeds": [0, 1, 2], "hand_size": 7,
    }
    if config:
        settings.update(json.loads(config.read_text()))
    space = DeckSpace(CARDS, tuple(settings["minimum"]), tuple(settings["maximum"]), settings["size"])
    initial = space.validate(settings["initial"])
    click.echo(json.dumps({"types": [c.name for c in CARDS], "initial": initial,
                           "initial_hands": sum(1 for _ in hand_distribution(dict(zip(CARDS, initial)),
                                                                            settings["hand_size"]))}))
    for seed in seeds or settings["seeds"]:
        for algorithm in ("discrete", "leitwerk") if method == "both" else (method,):
            objective = Objective(space, score_hand, budget or settings["budget"], settings["hand_size"])
            result = optimize(objective, initial, algorithm, seed)
            click.echo(json.dumps({"method": algorithm, "seed": seed, "baseline_score": objective.cache[initial],
                                   **asdict(result)}))


if __name__ == "__main__":
    main()
