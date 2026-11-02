"""Reproducible exact optimum, per-card crossings and casting-coverage report."""
import csv
import json
from collections import Counter
from fractions import Fraction
from math import lcm
from pathlib import Path

import click

from mana_analysis import LANDS, ROOT, card_label, casting_modes, percentage, probability, read_deck
from mana_basic_search import CAPACITIES, NAMES, evaluate_pool
from mana_fitness import mode_weights
from mana_sensitivity import land_swap, lexical_key, next_crossing

PAINFUL = ("Overgrown Tomb", "Watery Grave", "Breeding Pool", "Starting Town")


def validate_deck(deck: Counter) -> None:
    if any(type(n) is not int or n < 0 for n in deck.values()) or sum(deck.values()) != 60:
        raise ValueError("Every main deck must contain exactly 60 nonnegative integer card counts")
    if not any(n for name, n in deck.items() if name not in LANDS):
        raise ValueError("The deck must contain nonlands")
    supported = set(LANDS) | {mode.card for mode in casting_modes()}
    if any(n and name not in supported for name, n in deck.items()):
        raise ValueError("The deck contains unsupported cards")
    if any(n > 4 for name, n in deck.items() if name not in ("Swamp", "Island", "Forest")):
        raise ValueError("Nonbasic cards have a four-copy limit")


def revise_deck(original: Counter, changes: dict) -> Counter:
    validate_deck(original)
    revised = original.copy()
    spells = {mode.card for mode in casting_modes()}
    for name, delta in changes.items():
        if name not in spells or type(delta) is not int:
            raise ValueError("Spell changes must map supported nonland names to integer deltas")
        revised[name] += delta
    validate_deck(revised)
    return Counter({name: n for name, n in revised.items() if n})


class Evaluation:
    def __init__(self, deck: Counter, weights: dict[str, Fraction], penalty: Fraction, cache: dict, progress=None):
        validate_deck(deck)
        self.deck, self.penalty = deck, penalty
        self.modes = [m for m in casting_modes() if deck[m.card]]
        mode_weights(deck, self.modes, weights)  # Check coverage and weight names.
        self.cards = tuple(name for name, n in deck.items() if n and name not in LANDS)
        self.weights = {name: weights.get(name, Fraction(1)) for name in self.cards}
        if any(w <= 0 for w in self.weights.values()):
            raise ValueError("Baseline card weights must be positive; downward sensitivity can reach zero")
        self.bases, original_scores, original_denominator, self.components = evaluate_pool(deck, cache, progress)
        self.indices = {base: i for i, base in enumerate(self.bases)}
        counts = Counter(m.card for m in self.modes)
        coefficients = {name: Counter() for name in self.cards}
        for mode in self.modes:
            key = self.requirement(mode)
            for side in range(2):
                denominator = self.components[key][side][1]
                coefficients[mode.card][key, side] += Fraction(1, 2*counts[mode.card]*denominator)
        self.pden = lcm(*(c.denominator for terms in coefficients.values() for c in terms.values()))
        self.probabilities = {}
        for card, terms in coefficients.items():
            values = [0]*len(self.bases)
            for (key, side), coefficient in terms.items():
                factor = coefficient.numerator*(self.pden//coefficient.denominator)
                values = [a+int(b)*factor for a, b in zip(values, self.components[key][side][0])]
            self.probabilities[card] = values
        weight_scale = lcm(*(w.denominator for w in self.weights.values()))
        self.masses = {name: int(deck[name]*self.weights[name]*weight_scale) for name in self.cards}
        self.total_mass = sum(self.masses.values())
        self.raw = [0]*len(self.bases)
        for name, mass in self.masses.items():
            self.raw = [a+mass*b for a, b in zip(self.raw, self.probabilities[name])]
        self.k = [sum(base[NAMES.index(name)] for name in PAINFUL) for base in self.bases]
        self.a = [penalty.denominator*s-penalty.numerator*self.pden*self.total_mass*k
                  for s, k in zip(self.raw, self.k)]
        self.denominator = penalty.denominator*self.pden*self.total_mass
        maximum = max(self.a)
        self.ties = [i for i, value in enumerate(self.a) if value == maximum]
        self.winner = min(self.ties, key=lambda i: lexical_key(self.bases[i], NAMES))
        if all(w == 1 for w in self.weights.values()):
            for i in (0, len(self.bases)//2, self.winner, len(self.bases)-1):
                assert Fraction(self.raw[i], self.pden*self.total_mass) == Fraction(
                    original_scores[self.bases[i]], original_denominator)

    def requirement(self, mode) -> tuple:
        return mode.total, "".join(sorted(mode.colored)), mode.creature, self.deck[mode.card]

    def full_deck(self, index: int) -> Counter:
        deck = Counter({name: n for name, n in self.deck.items() if name not in LANDS})
        deck.update({name: n for name, n in zip(NAMES, self.bases[index]) if n})
        validate_deck(deck)
        assert self.bases[index][0] >= 1
        assert all(0 <= n <= cap for n, cap in zip(self.bases[index], CAPACITIES))
        return deck

    def describe(self, index: int) -> dict:
        ordinary = sum(self.deck[c]*self.probabilities[c][index] for c in self.cards)
        return dict(composition=dict(zip(NAMES, self.bases[index])), nonlands={c: self.deck[c] for c in self.cards},
                    card_weights=self.weights, ordinary_success=Fraction(ordinary, sum(self.deck[c] for c in self.cards)*self.pden),
                    weighted_success=Fraction(self.raw[index], self.pden*self.total_mass),
                    penalty=self.penalty*self.k[index], fitness=Fraction(self.a[index], self.denominator),
                    loss=1-Fraction(self.a[index], self.denominator), penalized_lands=self.k[index],
                    shocks=sum(self.bases[index][NAMES.index(n)] for n in PAINFUL[:-1]),
                    basic_lands=sum(self.bases[index][NAMES.index(n)] for n in ("Swamp", "Island", "Forest")))

    def sensitivities(self, cards: tuple[str, ...] | None = None, progress=None) -> list[dict]:
        rows = []
        baseline = self.winner
        selected = self.cards if cards is None else cards
        for position, card in enumerate(selected, 1):
            mass = self.masses[card]
            slopes = [mass*(self.penalty.denominator*p-self.penalty.numerator*self.pden*k)
                      for p, k in zip(self.probabilities[card], self.k)]
            lines = [(a-b, b) for a, b in zip(self.a, slopes)]
            row = dict(card=card, copies=self.deck[card], weight=self.weights[card],
                       current_castability=Fraction(self.probabilities[card][baseline], self.pden))
            for label, direction in (("less", -1), ("more", 1)):
                crossing = next_crossing(lines, self.bases, baseline, direction, NAMES)
                if crossing is None:
                    row[label] = dict(status="no_crossing")
                    continue
                successor = crossing.successor
                self.full_deck(successor)
                delta = Fraction(self.a[successor]-self.a[baseline], self.denominator)
                assert delta <= 0
                row[label] = dict(status=crossing.status, multiplier=crossing.multiplier,
                                  absolute_weight=self.weights[card]*crossing.multiplier,
                                  successor_from=crossing.lower, successor_to=crossing.upper,
                                  swap=land_swap(self.bases[baseline], self.bases[successor], NAMES),
                                  composition=dict(zip(NAMES, self.bases[successor])),
                                  target_castability=Fraction(self.probabilities[card][successor], self.pden),
                                  delta_target=Fraction(self.probabilities[card][successor]
                                                        -self.probabilities[card][baseline], self.pden),
                                  delta_baseline_fitness=delta, baseline_cost=-delta,
                                  overall_gain_at_crossing=Fraction(0))
            rows.append(row)
            if progress:
                progress(position, len(selected), f"Crossings: {card}")
            else:
                print(f"Crossings complete: {card}", flush=True)
        return rows

    def curves(self, progress=None) -> list[dict]:
        deck = self.full_deck(self.winner)
        rows, cache = [], {}
        for position, mode in enumerate(self.modes, 1):
            cells = {side: [] for side in ("play", "draw")}
            key = self.requirement(mode)
            for turn in range(1, 7):
                for side, extra in (("play", 6), ("draw", 7)):
                    if turn < mode.total:
                        value = None
                    elif turn == mode.total:
                        values, denominator = self.components[key][side == "draw"]
                        value = Fraction(int(values[self.winner]), denominator)
                    else:
                        cache_key = key, turn, extra
                        if cache_key not in cache:
                            cache[cache_key] = probability(deck, mode, turn+extra, turn)[0]
                        value = cache[cache_key]
                    cells[side].append(value)
            rows.append(dict(card=card_label(mode), cost=mode.cost, **cells))
            if progress:
                progress(position, len(self.modes), f"Coverage: {mode.card} {mode.cost}")
            else:
                print(f"T1-T6 complete: {mode.card} {mode.cost}", flush=True)
        return rows


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


def swap_text(swap: dict) -> str:
    def cards(counts):
        return ", ".join(f"{n} {name}" for name, n in counts.items()) or "none"
    return f"OUT: {cards(swap['out'])}<br>IN: {cards(swap['in'])}"


def suggestion_text(suggestion: dict, direction: str) -> str:
    if suggestion["status"] == "no_crossing":
        return "No change through weight zero" if direction == "less" else "No crossing at any higher weight"
    if suggestion["status"] == "boundary_tie":
        return "Tie only at weight zero; no admissible flip<br>"+swap_text(suggestion["swap"])
    relation = "below" if direction == "less" else "above"
    prefix = "Already tied at current weight" if suggestion["status"] == "already_tied" else (
        f"{relation.capitalize()} ×{float(suggestion['multiplier']):.6f}")
    return (prefix+"<br>"+swap_text(suggestion["swap"])
            + f"<br>Δcard {float(suggestion['delta_target'])*100:+.6f} pp; "
            f"baseline cost {float(suggestion['baseline_cost'])*100:+.6f} pp")


def build_report(original: Counter, changes: dict, weights: dict[str, Fraction], penalty: Fraction,
                 output: Path) -> dict:
    revised = revise_deck(original, changes)
    if penalty < 0:
        raise ValueError("Penalty must be nonnegative")
    cache = {}
    print("Evaluating original spell package", flush=True)
    old = Evaluation(original, weights, penalty, cache)
    print("Evaluating revised spell package; reusing unchanged requirement components", flush=True)
    current = Evaluation(revised, weights, penalty, cache)
    suggestions = current.sensitivities()
    old_index = current.indices[old.bases[old.winner]]
    comparison = dict(original=old.describe(old.winner), revised=current.describe(current.winner),
                      original_lands_under_revised_package=current.describe(old_index),
                      land_swap=land_swap(old.bases[old.winner], current.bases[current.winner], NAMES),
                      land_adjustment_gain=Fraction(current.a[current.winner]-current.a[old_index],
                                                   current.denominator))
    if "Awaken the Honored Dead" in old.cards:
        comparison["original_awaken_sensitivity"] = old.sensitivities(("Awaken the Honored Dead",))[0]
    old_full, new_full = old.full_deck(old.winner), current.full_deck(current.winner)
    all_names = sorted(set(old_full) | set(new_full))
    comparison["full_deck_swap"] = {
        "out": {n: old_full[n]-new_full[n] for n in all_names if old_full[n] > new_full[n]},
        "in": {n: new_full[n]-old_full[n] for n in all_names if new_full[n] > old_full[n]}}
    assert sum(comparison["full_deck_swap"]["out"].values()) == sum(
        comparison["full_deck_swap"]["in"].values())
    curves = current.curves()
    data = dict(deck_size=60, land_count=26, candidates=len(current.bases), land_names=NAMES,
                land_caps=CAPACITIES, penalty=penalty, changes=changes, optimal_ties=len(current.ties),
                optimum=current.describe(current.winner), suggestions=suggestions,
                package_comparison=comparison, castability=curves)
    write_report(output, data)
    deck_text = "Deck\n"+"\n".join(f"{n} {name} (MODEL) 0" for name, n in new_full.items())+"\n"
    output.with_suffix(".deck.txt").write_text(deck_text, encoding="utf-8")
    return data


def write_report(output: Path, data: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(exact_json(data), indent=2), encoding="utf-8")
    with output.with_suffix(".csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["card", "copies", "direction", "status", "multiplier", "absolute_weight", "out", "in",
                         "delta_card_fraction", "baseline_fitness_cost_fraction", "overall_gain_at_crossing_fraction"])
        for row in data["suggestions"]:
            for direction in ("less", "more"):
                entry = row[direction]
                swap = entry.get("swap", {})
                writer.writerow([row["card"], row["copies"], direction, entry["status"],
                                 str(entry.get("multiplier", "")), str(entry.get("absolute_weight", "")),
                                 json.dumps(swap.get("out", {})), json.dumps(swap.get("in", {})),
                                 str(entry.get("delta_target", "")), str(entry.get("baseline_cost", "")),
                                 str(entry.get("overall_gain_at_crossing", ""))])
    optimum = data["optimum"]
    text = ["# Mana optimum and per-card swap suggestions", "",
            "Every deck contains exactly 60 cards: 26 lands and 34 nonlands. Suggestions replace lands only.",
            "The explicit nonland scenario is compared separately below; the input deck file is unchanged.",
            "Search is exhaustive within 59,109 bases: 1–2 Swamps, 0–1 Island, 0–1 Forest,",
            "and 0–4 each Sultai shock, Sultai Verge, Starting Town and Cavern. No Sewers or Passage.",
            f"Penalty λ={data['penalty']} ({float(data['penalty'])*100:g} percentage points per shock or Town).",
            "Fitness = normalized weighted color success − λ × (shocks + Towns); loss = 1 − fitness.", "",
            "## Optimum", "", "| Land | Copies |", "|---|---:|"]
    text.extend(f"| {name} | {count} |" for name, count in optimum["composition"].items() if count)
    text.extend(["| **Total lands** | **26** |", "", "| Nonland | Copies | Importance |", "|---|---:|---:|"])
    text.extend(f"| {name} | {count} | {float(optimum['card_weights'][name]):g} |"
                for name, count in optimum["nonlands"].items())
    text.extend(["| **Total nonlands** | **34** | |", "",
                 f"Raw color success: **{float(optimum['ordinary_success']):.6%}**. "
                 f"Weighted success: **{float(optimum['weighted_success']):.6%}**.",
                 f"Penalty contribution: **{float(optimum['penalty']):.6%}**. "
                 f"Regularized fitness: **{float(optimum['fitness']):.6%}**; "
                 f"loss: **{float(optimum['loss']):.6%}**.",
                 f"Co-optimal bases at current weights: {data['optimal_ties']}; "
                 "lexical counts select the printed base.",
                 "", "## Per-card sensitivity", "",
                 "Each direction varies only that card's importance, relative to its current value; "
                 "other weights and λ stay fixed. Copy weights are renormalized; modes and play/draw stay uniform.",
                 "A threshold is an exact optimum crossing, not an iterated search over guessed coefficients.",
                 "**At the crossing, overall fitness improvement is zero.** "
                 "The suggested base wins immediately beyond it.",
                 "Δcard is its change in conditional castability, averaged over modes/play/draw. "
                 "Baseline cost is the overall fitness sacrificed under the original weights "
                 "(both in percentage points).",
                 "Weights are renormalized while λ stays fixed. A weight change can therefore favor a "
                 "different shock/Town tradeoff even when Δcard is zero or has the unexpected sign; "
                 "the reported signed delta makes this explicit.",
                 "No arbitrary beyond-crossing probe contributes to the report. Endpoint ties at zero are not flips.",
                 "Simultaneous crossings choose the winning slope beyond the boundary, then minimum swaps, "
                 "then lexical land counts. Identical lines do not manufacture flips.", "",
                 "| Card | Value less | Value more |", "|---|---|---|"])
    text.extend(f"| {row['card']} | {suggestion_text(row['less'], 'less')} | "
                f"{suggestion_text(row['more'], 'more')} |" for row in data["suggestions"])
    comparison = data["package_comparison"]
    text.extend(["", "## Awaken / Bitter Triumph replacement", "",
                 "| Spell | Original copies | Revised copies |", "|---|---:|---:|"])
    text.extend(f"| {card} | {comparison['original']['nonlands'].get(card, 0)} | "
                f"{comparison['revised']['nonlands'].get(card, 0)} |" for card in data["changes"])
    text.extend(["", "| Land | Original-package optimum | Revised-package optimum |", "|---|---:|---:|"])
    text.extend(f"| {name} | {comparison['original']['composition'][name]} | "
                f"{comparison['revised']['composition'][name]} |" for name in NAMES
                if comparison["original"]["composition"][name] or comparison["revised"]["composition"][name])
    text.extend(["", "Combined 60-card change: "+swap_text(comparison["full_deck_swap"])+".",
                 "Native scores below belong to different spell packages and are not a win-rate comparison.", "",
                 "| Evaluation | Weighted color success | Regularized fitness |", "|---|---:|---:|"])
    for label, key in (("Original package, its optimum", "original"),
                       ("Revised package, original land base", "original_lands_under_revised_package"),
                       ("Revised package, revised optimum", "revised")):
        entry = comparison[key]
        text.append(f"| {label} | {float(entry['weighted_success']):.6%} | {float(entry['fitness']):.6%} |")
    text.extend(["", "Gain from adapting the lands, evaluated under the **same revised package**: "
                 f"**{float(comparison['land_adjustment_gain'])*100:.6f} percentage points**.", "",
                 "## Casting coverage of the revised optimum", "",
                 "Seven-card keeps; see T+6 cards on the play or T+7 on the draw. Each percentage conditions on",
                 "seeing the target and enough lands for that payment. Choose the best subset of up to T lands.",
                 "Ignore draw order, tapped entry, actual life payments, nonmana costs, targets, ramp, extra draws",
                 "and mulligans. Cavern casts every creature; Verge activation uses actual chosen basic types.",
                 "Single-effect rows include both-effect payments; rows overlap. Spider-Man copy targets and",
                 "Sunderflock discount enablers are assumed available, not established by a rollout.",
                 "The metric includes earliest turns beyond T6 (e.g. Sunderflock T8/T9), despite this table's range.",
                 "— means unavailable before the total cost's turn. Percentages have at most one decimal."])
    for side, title in (("play", "On the play"), ("draw", "On the draw")):
        text.extend(["", f"### {title}", "", "| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |",
                     "|---|---|---:|---:|---:|---:|---:|---:|"])
        text.extend(f"| {row['card']} | {row['cost']} | "
                    + " | ".join("—" if p is None else percentage(p) for p in row[side])+" |"
                    for row in data["castability"])
    text.extend(["", "All probabilities, crossings and score comparisons use exact rational/integer arithmetic.",
                 "Displayed values are rounded. JSON retains fractions, candidate compositions "
                 "and successor intervals; CSV contains the sensitivity rows.",
                 "The companion .deck.txt exports the revised optimal 60-card deck.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")


def load_config(context: click.Context, parameter: click.Parameter, path: Path | None) -> None:
    if path is None or context.resilient_parsing:
        return
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(values, dict) or set(values)-{"deck", "penalty", "changes", "weights", "output"}:
            raise ValueError("Unknown report configuration field")
        for name in ("changes", "weights"):
            if name in values:
                values[name] = json.dumps(values[name])
        for name in ("deck", "output"):
            if name in values and not Path(values[name]).is_absolute():
                values[name] = str(path.resolve().parent / values[name])
    except (OSError, ValueError, TypeError) as error:
        raise click.BadParameter(str(error), param_hint="config") from error
    context.default_map = {**(context.default_map or {}), **values}


@click.command()
@click.option("--config", type=click.Path(exists=True, path_type=Path), is_eager=True,
              expose_value=False, callback=load_config)
@click.option("--deck", type=click.Path(exists=True, path_type=Path),
              default=ROOT / "resources/decks/evoke_elementals.txt")
@click.option("--changes", default="{}", help="JSON object of physical nonland copy-count deltas; must sum to zero.")
@click.option("--weights", default="{}", help="JSON object of positive per-card importance weights.")
@click.option("--penalty", default="0.0032", help="Exact normalized penalty per shock or Town.")
@click.option("--output", type=click.Path(path_type=Path), default=ROOT / "reports/mana-report")
def main(deck: Path, changes: str, weights: str, penalty: str, output: Path) -> None:
    try:
        deltas, importance = json.loads(changes), json.loads(weights)
        if not isinstance(deltas, dict) or not isinstance(importance, dict):
            raise ValueError("Changes and weights must be JSON objects")
        parsed_weights = {name: Fraction(str(value)) for name, value in importance.items()}
        build_report(read_deck(deck), deltas, parsed_weights, Fraction(penalty), output)
    except (ValueError, ZeroDivisionError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Full report: {output.with_suffix('.md')}")


if __name__ == "__main__":
    main()
