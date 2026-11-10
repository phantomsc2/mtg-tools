"""Import main-deck printed nonland costs from Scryfall, without local persistence."""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import monotonic, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mana_opportunities import SpellCost

COLLECTION_URL = "https://api.scryfall.com/cards/collection"
FRONT_FACE_LAYOUTS = frozenset(("transform", "modal_dfc", "adventure", "flip"))


class DecklistImportError(ValueError):
    """All actionable diagnostics from one failed import; no partial result."""

    def __init__(self, diagnostics: Sequence[str]) -> None:
        self.diagnostics = tuple(diagnostics)
        super().__init__("Decklist import failed:\n" + "\n".join(f"- {message}" for message in diagnostics))


@dataclass(frozen=True)
class DeckEntry:
    name: str
    count: int
    line: int


@dataclass(frozen=True)
class ImportedSpell:
    name: str
    cost: str
    count: int


@dataclass(frozen=True)
class ImportedDeck:
    rows: tuple[ImportedSpell, ...]
    excluded_land_count: int

    @property
    def spells(self) -> tuple[SpellCost, ...]:
        return tuple(SpellCost(row.cost, row.count) for row in self.rows)


def parse_decklist(text: str) -> tuple[DeckEntry, ...]:
    """Read quantity/name lines, ignoring printing annotations and the sideboard."""
    entries, errors = [], []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.casefold() == "sideboard":
            break
        if not line or line.casefold() == "deck":
            continue
        match = re.fullmatch(r"([1-9][0-9]*)\s+(.+)", line)
        if not match:
            errors.append(f"Line {number}: expected a positive quantity followed by a card name: {line!r}")
            continue
        count, name = match.groups()
        name = re.sub(r"\s+\([A-Za-z0-9]+\)\s+\S+$", "", name).strip()
        entries.append(DeckEntry(name, int(count), number))
    if not entries and not errors:
        errors.append("The main deck is empty.")
    if errors:
        raise DecklistImportError(errors)
    return tuple(entries)


def fetch_cards(names: Sequence[str]) -> tuple[dict[str, Any], ...]:
    """Batch exact names; all response data lives only in memory for this call."""
    unique = list({name.casefold(): name for name in names}.values())
    cards = []
    last_request = None
    for start in range(0, len(unique), 75):
        if last_request is not None:
            sleep(max(0, 0.5 - (monotonic() - last_request)))
        request = Request(
            COLLECTION_URL,
            data=json.dumps({"identifiers": [{"name": name} for name in unique[start:start + 75]]}).encode(),
            headers={"User-Agent": "mtg-tools/0.1", "Accept": "application/json", "Content-Type": "application/json"},
            method="POST",
        )
        last_request = monotonic()
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as error:
            message = f"Scryfall returned HTTP {error.code}: {error.reason}. Try again later."
            raise DecklistImportError([message]) from error
        except (URLError, OSError) as error:
            raise DecklistImportError([f"Could not reach Scryfall: {error}"]) from error
        except ValueError as error:
            raise DecklistImportError(["Scryfall returned invalid JSON."]) from error
        if (not isinstance(payload, dict) or payload.get("object") != "list"
                or not isinstance(payload.get("data"), list)
                or any(not isinstance(card, dict) or not isinstance(card.get("name"), str)
                       or not (card.get("oracle_id") or card.get("id")) for card in payload["data"])):
            raise DecklistImportError(["Scryfall returned an unexpected collection response."])
        cards.extend(payload["data"])
    return tuple(cards)


def _front(card: Mapping[str, Any]) -> Mapping[str, Any]:
    layout = card.get("layout")
    if layout == "split":
        raise ValueError("split cards are unsupported")
    faces = card.get("card_faces")
    if faces:
        if layout not in FRONT_FACE_LAYOUTS:
            raise ValueError(f"unsupported multiface layout {layout!r}")
        return faces[0]
    return card


def _cost(mana_cost: str | None) -> str:
    if not mana_cost:
        raise ValueError("no printed mana cost (this is not a zero-cost spell)")
    if not re.fullmatch(r"(?:\{(?:0|[1-9][0-9]*|[WUBRG])\})+", mana_cost):
        raise ValueError(f"unsupported printed mana cost {mana_cost!r}; only generic and WUBRG mana are supported")
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    generic = sum(int(symbol) for symbol in symbols if symbol.isdecimal())
    colored = "".join(symbol for symbol in symbols if not symbol.isdecimal())
    return SpellCost((str(generic) if generic else "") + colored or "0", 1).cost


def _convert(entries: Sequence[DeckEntry], cards: Sequence[Mapping[str, Any]]) -> ImportedDeck:
    # Index aliases explicitly: collection response order is not request order.
    aliases = {}
    for card in cards:
        aliases[card["name"].casefold()] = card
        faces = card.get("card_faces")
        if faces:
            aliases[faces[0]["name"].casefold()] = card

    grouped, errors = {}, []
    for entry in entries:
        card = aliases.get(entry.name.casefold())
        if card is None:
            errors.append(f"Line {entry.line}, {entry.name}: no exact card or front-face name found in Scryfall")
            continue
        identity = card.get("oracle_id") or card["id"]
        previous = grouped.get(identity)
        grouped[identity] = (card, entry.count + (previous[1] if previous else 0))

    rows, lands = [], 0
    for card, count in grouped.values():
        try:
            front = _front(card)
            type_line = front.get("type_line")
            if not type_line:
                raise ValueError("missing card type")
            if "Land" in type_line.split("—", 1)[0].split():
                lands += count
                continue
            cost = _cost(front.get("mana_cost"))
            rows.append(ImportedSpell(front["name"], cost, count))
        except ValueError as error:
            errors.append(f"{card['name']}: {error}")
    if errors:
        raise DecklistImportError(errors)
    return ImportedDeck(tuple(rows), lands)


def import_decklist(text: str) -> ImportedDeck:
    """Resolve all main-deck cards and return only their ordinary nonland costs.

    Printing annotations and format legality are ignored. A failed lookup or an
    unsupported nonland raises DecklistImportError instead of returning a partial
    spell package. Every invocation makes fresh requests; nothing is saved.
    """
    entries = parse_decklist(text)
    return _convert(entries, fetch_cards([entry.name for entry in entries]))


def format_spells(result: ImportedDeck) -> str:
    """Return a copyable SPELLS assignment with a comment naming each card."""
    lines = [f"    SpellCost({row.cost!r}, {row.count}),  # {row.name}" for row in result.rows]
    return "\n".join(("SPELLS = (", *lines, ")"))
