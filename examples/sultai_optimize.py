"""Bounded, reproducible Sultai search: python -m examples.sultai_optimize."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from examples.sultai import LAND_NAMES, MANA_BASE, SPELLS
from mana_lands import ManaSource, STANDARD_AS_OF
from mana_opportunities import Spell, spell_components
from mana_search import LocalManaEvaluator, ManaSpace, local_search

LAND_COUNT = 26
COLORS = "UBG"
FORMAT = "standard"
LAND_FAMILIES = {
    "basic": (0, 2), "shock": (0, 4), "fast": (0, 4),
    "verge": (0, 4), "town": (0, 4), "tri": (0, 2),
}
FIXED_LANDS = {ManaSource("WUBRG", "cavern"): 4, ManaSource("WUBRG", "town"): 4,
               ManaSource("BG", "tapped"): 2}
SHOCK_PENALTY = 0.012
TOWN_PENALTY = 0.015
TURNS = 7
POSITION = "both"
OPENING_HAND_SIZE = 7
EVALUATION_BUDGETS = (200, 150, 150)


def make_space():
    return ManaSpace.from_colors(LAND_COUNT, COLORS, format=FORMAT,
                                 families=LAND_FAMILIES, fixed=FIXED_LANDS)


def starting_bases():
    palace, tomb = ManaSource("UBG", "tri"), ManaSource("BG", "shock", "BG")
    bases = [dict(MANA_BASE) for _ in range(3)]
    targets = (1, 0, 2) if MANA_BASE.get(palace, 0) == 1 else (0, 1, 2)
    for base, target in zip(bases, targets):
        change = target - base.get(palace, 0)
        base[palace] = target
        base[tomb] -= change
    return tuple(bases)


def optimize(evaluator, *, budgets=EVALUATION_BUDGETS,
             shock_penalty=SHOCK_PENALTY, town_penalty=TOWN_PENALTY, progress=None):
    """Share component caches across three starts; budgets count visits per run."""
    if len(budgets) != 3:
        raise ValueError("Supply one evaluation budget for each of the three starts")
    runs = []
    for index, (base, budget) in enumerate(zip(starting_bases(), budgets)):
        if progress:
            progress(index, 0, None)
        runs.append(local_search(
            evaluator, base, evaluation_budget=budget,
            shock_penalty=shock_penalty, town_penalty=town_penalty,
            progress=(lambda n, best, i=index: progress(i, n, best)) if progress else None,
        ))
    winner = min((r.best for r in runs), key=lambda row: (-row.score, row.counts))
    return tuple(runs), winner


def make_report(evaluator, runs, winner, seconds, *, budgets=EVALUATION_BUDGETS,
                shock_penalty=SHOCK_PENALTY, town_penalty=TOWN_PENALTY):
    space = evaluator.space
    baseline = evaluator.value(MANA_BASE, shock_penalty=shock_penalty, town_penalty=town_penalty)
    base = dict(zip(space.sources, winner.counts))
    divisor = TURNS * 2
    before, after = evaluator.components(MANA_BASE), evaluator.components(base)
    assert spell_components(SPELLS)[0] + sum(MANA_BASE.values()) == 60
    assert winner.score >= baseline.score
    assert sum(run.evaluations for run in runs) <= sum(budgets)
    for counts in evaluator.cache:
        space.counts(dict(zip(space.sources, counts)))
    by_cost = {}
    for column, result in zip(("initial", "result"), (before, after)):
        for row in result.opportunities:
            values = by_cost.setdefault(row.cost, {"initial": 0.0, "result": 0.0})
            values[column] += row.weighted_contribution / divisor
    for values in by_cost.values():
        values["delta"] = values["result"] - values["initial"]
    return {
        "standard_as_of": STANDARD_AS_OF,
        "settings": {"land_count": LAND_COUNT, "colors": COLORS, "format": FORMAT,
                     "turns": TURNS, "position": POSITION, "opening_hand_size": OPENING_HAND_SIZE,
                     "shock_penalty": shock_penalty, "town_penalty": town_penalty,
                     "budgets": list(budgets), "palace_limit": 2},
        "source_bounds": {LAND_NAMES[s]: list(bounds) for s, bounds in space.bounds.items()},
        "spell_profiles": [
            {"count": spell.count, "weight": spell.weight,
             "modes": [{"cost": m.cost, "weight": m.weight} for m in spell.modes]
             if isinstance(spell, Spell) else [{"cost": spell.cost, "weight": 1}]}
            for spell in SPELLS
        ],
        "assumptions": [
            "V1: seen-land color coverage and independent land availability are separate.",
            "Cavern is unrestricted rainbow mana; creature and chosen-type restrictions are ignored.",
            "Incarnation modes target enters effects, omitting mixed evoke payments with no effect.",
            "Spider-Man includes colored-payment scenarios for copied incarnation effects.",
            "Sunderflock scenarios: 7UU, 2UU, 1UU; board presence is not simulated.",
            "Mode shares and spell importance are uniform; four Awaken and two Glarb, no Overlord.",
            "No sequencing, mulligans, life simulation, or global-optimum guarantee.",
        ],
        "pool_candidates": space.candidate_count(),
        "initial": {LAND_NAMES[s]: n for s, n in MANA_BASE.items() if n},
        "lands": {LAND_NAMES[s]: n for s, n in base.items() if n},
        "out": {LAND_NAMES[s]: MANA_BASE.get(s, 0)-n for s, n in base.items() if MANA_BASE.get(s, 0)>n},
        "in": {LAND_NAMES[s]: n-MANA_BASE.get(s, 0) for s, n in base.items() if n>MANA_BASE.get(s, 0)},
        "baseline_score": float(baseline.score), "score": float(winner.score),
        "exact_baseline_score": str(baseline.score), "exact_score": str(winner.score),
        "raw_opportunities": float(winner.raw_score), "penalty": float(winner.penalty),
        "delta": float(winner.score-baseline.score),
        "seconds": seconds, "unique_evaluations": len(evaluator.cache),
        "runs": [{"initial_palaces": base.get(ManaSource("UBG", "tri"), 0),
                  "budget": budget, "evaluations": run.evaluations,
                  "seconds": run.seconds, "stopped": run.stopped, "score": float(run.best.score),
                  "counts": list(run.best.counts)}
                 for base, budget, run in zip(starting_bases(), budgets, runs)],
        "source_order": [LAND_NAMES[s] for s in space.sources],
        "weighted_opportunities_by_cost": by_cost,
    }


def markdown_report(report):
    lines = ["# Sultai optimization with at most two Opulent Palaces", "",
             "Best found by deterministic bounded local search; no global-optimum claim.", "",
             "| Land | Initial | Result |", "| --- | ---: | ---: |"]
    for name in sorted(report["initial"].keys() | report["lands"].keys()):
        lines.append(f'| {name} | {report["initial"].get(name, 0)} | {report["lands"].get(name, 0)} |')
    lines += ["| **Total** | **26** | **26** |", "",
              f'Score: {report["baseline_score"]:.9f} → {report["score"]:.9f} '
              f'(delta {report["delta"]:+.9f}). These are opportunity scores, not win rates.', "",
              f'{report["unique_evaluations"]} distinct bases evaluated in {report["seconds"]:.2f}s. '
              f'Filtered pool contains {report["pool_candidates"]:,} compositions; no global grid was built.', "",
              "| Initial Palaces | Budget | Visits | Seconds | Stop | Score |",
              "| ---: | ---: | ---: | ---: | --- | ---: |"]
    swaps = [f'{direction.upper()}: ' + ', '.join(f'{n} {name}' for name, n in report[direction].items())
             for direction in ("out", "in")]
    run_table = lines.index("| Initial Palaces | Budget | Visits | Seconds | Stop | Score |")
    lines[run_table:run_table] = [swaps[0], "", swaps[1], ""]
    for run in report["runs"]:
        lines.append(f'| {run["initial_palaces"]} | {run["budget"]} | {run["evaluations"]} | '
                     f'{run["seconds"]:.2f} | {run["stopped"]} | {run["score"]:.9f} |')
    lines += ["", "## Per-cost weighted opportunities", "",
              "| Cost | Initial | Result | Delta |", "| --- | ---: | ---: | ---: |"]
    for cost, values in sorted(report["weighted_opportunities_by_cost"].items()):
        lines.append(f'| {cost} | {values["initial"]:.9f} | {values["result"]:.9f} | {values["delta"]:+.9f} |')
    lines += ["", "## Settings and assumptions", "",
              "```json", json.dumps(report["settings"], indent=2), "```", ""]
    lines += [f'- {assumption}' for assumption in report["assumptions"]]
    lines += ["", f'Standard snapshot checked as of {report["standard_as_of"]}.', "",
              "Legality evidence: [Standard sets](https://magic.wizards.com/en/formats/standard), "
              "[TDM checklist](https://media.wizards.com/ContentResources/WPN/deck_checklists/tdm/MTGTDM_EN_DkCklst.pdf).", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/sultai_palace_optimization.json"))
    args = parser.parse_args()
    evaluator = LocalManaEvaluator(make_space(), SPELLS, turns=TURNS, position=POSITION,
                                   opening_hand_size=OPENING_HAND_SIZE, family_maximums={"basic": 2})
    def progress(index, visits, best):
        score = f"; best {float(best.score):.9f}" if best else ""
        print(f"Start {index+1}: {visits} bases visited{score}", flush=True)
    started = perf_counter()
    runs, winner = optimize(evaluator, progress=progress)
    report = make_report(evaluator, runs, winner, perf_counter()-started)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"lands": report["lands"], "score": report["score"], "delta": report["delta"]}, indent=2))


if __name__ == "__main__":
    main()
