"""Exact conditional color coverage, without simulation or floating-point summation."""
import argparse
import csv
import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import product
from math import comb, prod
from pathlib import Path

from hands import compositions

ROOT = Path(__file__).resolve().parent
COLORS = "WUBRG"


@dataclass(frozen=True)
class Land:
    colors: str
    types: str = ""
    conditional: str = ""
    requires: str = ""
    cavern: bool = False


LANDS = {
    "Overgrown Tomb": Land("BG", "BG"),
    "Watery Grave": Land("UB", "UB"),
    "Swamp": Land("B", "B"),
    "Island": Land("U", "U"),
    "Forest": Land("G", "G"),
    "Cavern of Souls": Land("", cavern=True),
    "Starting Town": Land(COLORS),
    "Gloomlake Verge": Land("U", conditional="B", requires="UB"),
    "Breeding Pool": Land("UG", "UG"),
    "Wastewood Verge": Land("G", conditional="B", requires="BG"),
    "Willowrush Verge": Land("U", conditional="G", requires="UG"),
    "Undercity Sewers": Land("UB", "UB"),
}


@dataclass(frozen=True)
class Mode:
    card: str
    label: str
    generic: int
    colored: str
    creature: bool = True
    scenario: str = ""

    @property
    def total(self) -> int:
        return self.generic + len(self.colored)

    @property
    def cost(self) -> str:
        return (str(self.generic) if self.generic else "") + self.colored


def casting_modes() -> list[Mode]:
    modes = [Mode("Superior Spider-Man", "Normal", 2, "UB")]
    for elemental, payments in [
        ("Deceit", [("B effect", 1, "BBU"), ("U effect", 1, "BUU"), ("both effects", 0, "BBUU")]),
        ("Wistfulness", [("U effect", 1, "BUU"), ("G effect", 0, "BUGG")]),
        ("Emptiness", [("B effect", 1, "BBU"), ("W effect", 0, "BUWW")]),
    ]:
        modes.extend(Mode("Superior Spider-Man", f"Copy {elemental}: {effect}", generic, colored,
                          scenario=f"Assume {elemental} available in a graveyard")
                     for effect, generic, colored in payments)
    for card, generic, colors in [("Deceit", 4, "UB"), ("Wistfulness", 3, "GU"),
                                   ("Emptiness", 4, "WB")]:
        modes.extend(Mode(card, f"Evoke: {c} effect", 0, c * 2) for c in colors)
        modes.extend(Mode(card, f"Normal: {c} effect", generic, c * 2) for c in colors)
        modes.append(Mode(card, "Normal: both effects", generic - 2, colors[0] * 2 + colors[1] * 2))
    modes.extend([Mode("Formidable Speaker", "Normal", 2, "G"),
                  Mode("Bitter Triumph", "Normal", 1, "B", False),
                  Mode("Moonshadow", "Normal", 0, "B"),
                  Mode("Awaken the Honored Dead", "Normal", 0, "BGU", False)])
    # Elemental mana values in this list: Moonshadow 1, Wistfulness 5,
    # Deceit/Emptiness 6, Sunderflock 9. Discounts cannot remove UU.
    for discount in (0, 1, 5, 6, 9):
        modes.append(Mode("Sunderflock", f"Discount {discount}", max(0, 7 - discount), "UU",
                          scenario=(f"Assume greatest controlled Elemental MV = {discount}"
                                    if discount else "No Elemental discount")))
    return modes


def read_deck(path: Path) -> Counter:
    deck = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "Sideboard":
            break
        match = re.fullmatch(r"(\d+) (.+?) \([^)]+\) \S+", line.strip())
        if match:
            deck[match[2]] += int(match[1])
        elif line.strip() and line.strip() != "Deck":
            raise ValueError(f"Unrecognized deck line: {line}")
    return deck


@lru_cache(maxsize=200000)
def can_pay(lands: tuple[Land, ...], counts: tuple[int, ...], total: int,
            colored: str, creature: bool, land_limit: int | None = None) -> bool:
    land_limit = total if land_limit is None else land_limit
    if land_limit < total:
        return False
    if sum(counts) < total:
        return False
    # Enumerate legal chosen battlefields, including lands used for generic mana.
    selected_count = min(land_limit, sum(counts))
    required = Counter(colored)
    color_list = tuple(required)
    tests = [(set(c for c, take in zip(color_list, bits) if take),
              sum(required[c] for c, take in zip(color_list, bits) if take))
             for bits in product((0, 1), repeat=len(color_list)) if any(bits)]
    def matches(selected: tuple[int, ...]) -> bool:
        types = set("".join(land.types for land, n in zip(lands, selected) if n))
        sources = []
        for land, n in zip(lands, selected):
            colors = set(COLORS if land.cavern and creature else land.colors)
            if types.intersection(land.requires):
                colors.update(land.conditional)
            sources.append((colors, n))
        # Hall's matching condition: every subset of colored pips has enough
        # distinct sources. Same-color pips have identical neighborhoods.
        return all(sum(n for colors, n in sources if colors.intersection(group)) >= needed
                   for group, needed in tests)

    # An optimistic all-lands check avoids enumerating subsets that cannot work.
    if not matches(counts):
        return False
    if sum(counts) <= land_limit:
        return True
    return any(matches(selected) for selected in compositions(counts, selected_count))


def probability(deck: Counter, mode: Mode, seen: int, turn: int | None = None) -> tuple[Fraction | None, int, int]:
    return _probability(tuple(deck.items()), mode.card, mode.total, mode.colored,
                        mode.creature, seen, mode.total if turn is None else turn)


@lru_cache(maxsize=None)
def _probability(deck_items: tuple[tuple[str, int], ...], card: str, total: int,
                 colored: str, creature: bool, seen: int, turn: int) -> tuple[Fraction | None, int, int]:
    deck = Counter(dict(deck_items))
    names = tuple(name for name in deck if name in LANDS)
    lands = tuple(LANDS[name] for name in names)
    capacities = tuple(deck[name] for name in names)
    nonlands = sum(deck.values()) - sum(capacities)
    copies = deck[card]
    success = denominator = 0
    for land_count in range(total, min(sum(capacities), seen - 1) + 1):
        remaining = seen - land_count
        if remaining > nonlands:
            continue
        # All nonland draws minus draws containing zero target copies.
        spell_weight = comb(nonlands, remaining) - (comb(nonlands - copies, remaining)
                       if remaining <= nonlands - copies else 0)
        for counts in compositions(capacities, land_count):
            weight = prod(comb(n, k) for n, k in zip(capacities, counts)) * spell_weight
            denominator += weight
            if can_pay(lands, counts, total, colored, creature, turn):
                success += weight
    return (Fraction(success, denominator) if denominator else None), success, denominator


def percentage(value: Fraction | None) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}".rstrip("0").rstrip(".") + "%"


def card_label(mode: Mode) -> str:
    if mode.label.startswith("Copy "):
        return f"{mode.card} → {mode.label[5:].split(':')[0]}"
    return mode.card


def generate(deck_path: Path, output: Path) -> None:
    deck = read_deck(deck_path)
    modes = casting_modes()
    if set(deck) - set(LANDS) != {mode.card for mode in modes}:
        raise ValueError("Deck nonlands do not match the configured casting modes")
    rows = []
    table_rows = []
    for mode in modes:
        cells = {position: [] for position in ("play", "draw")}
        for turn in range(1, 7):
            row = dict(card=card_label(mode), cost=mode.cost, turn=turn)
            for position, extra in (("play", 6), ("draw", 7)):
                if turn < mode.total:
                    value, numerator, denominator = None, 0, 0
                    display = "—"
                else:
                    value, numerator, denominator = probability(deck, mode, turn + extra, turn)
                    display = percentage(value)
                cells[position].append(display)
                row[position] = display
                row[position + "_fraction"] = str(value) if value is not None else ""
                row[position + "_successful_weight"] = numerator
                row[position + "_conditioning_weight"] = denominator
            rows.append(row)
        table_rows.append((mode, cells))
        print(f"{mode.card}: {mode.label} {mode.cost}: complete", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.with_suffix(".csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    text = ["# Sultai evoke: exact conditional color coverage", "",
            f"Deck: {sum(deck.values())} cards, {sum(deck[n] for n in deck if n in LANDS)} lands. Main deck only.", "",
            "Each percentage is P(payment possible | target seen, lands seen >= total cost).",
            "Seven-card keeps; see T+6 cards on the play or T+7 on the draw. Choose up to T lands, including unused Verge enablers.",
            "Each column is evaluated on that turn. — means the cost exceeds the turn's land limit; N/A means an empty conditioning event.",
            "Ignore draw order, ETB tapped, life and nonmana costs, targets, ramp, extra draws and mulligans.",
            "Cavern supplies any creature color, but only colorless for noncreatures. Verge conditions remain active.",
            "Single-effect rows include payments enabling both effects; rows overlap and must not be added.",
            "Sunderflock scenarios assume the stated board without modeling its setup or conditioning on enabler draws.",
            "Spider-Man copy scenarios assume the elemental is in a graveyard; condition on Spider-Man seen, not the copied card.",
            "At four mana, Spider-Man can enable both Deceit effects, but cannot enable both Wistfulness or both Emptiness effects.",
            "Copying Moonshadow or Sunderflock adds no color requirement beyond Spider-Man's normal row.",
            "Sunderflock costs 7UU, 6UU, 2UU, 1UU and UU assume greatest Elemental MV 0, 1, 5, 6 and 9 respectively.",
            "CSV includes exact reduced fractions and integer event weights per turn. Percentages alone are rounded to at most one decimal."]
    for position, title in (("play", "On the play"), ("draw", "On the draw")):
        text.extend(["", f"## {title}", "", "| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |",
                     "|---|---|---:|---:|---:|---:|---:|---:|"])
        text.extend(f"| {card_label(mode)} | {mode.cost} | " + " | ".join(cells[position]) + " |"
                    for mode, cells in table_rows)
    text.extend(["", "## Mana-source inventory", "", "| Land | Copies | Colors | Basic types | Condition |",
                 "|---|---:|---|---|---|"])
    for name, n in deck.items():
        if name in LANDS:
            land = LANDS[name]
            colors = "Any for creatures; C otherwise" if land.cavern else land.colors
            condition = f"{land.conditional} requires {' or '.join(land.requires)} type" if land.requires else ""
            text.append(f"| {name} | {n} | {colors} | {land.types} | {condition} |")
    text.extend(["", "Metadata and mathematical details: [analysis notes](../ideas/knowledge/mana-analysis.md).", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deck", type=Path, default=ROOT / "resources/decks/evoke_elementals.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/sultai-mana")
    args = parser.parse_args()
    generate(args.deck, args.output)
