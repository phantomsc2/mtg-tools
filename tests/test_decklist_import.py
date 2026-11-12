import io
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from mtg_tools.decklist_import import DecklistImportError, fetch_cards, format_spells, import_decklist, parse_decklist
from mtg_tools.mana.spells import SpellCost, spell_components


SAMPLE_DECK = """4 Kaito, Bane of Nightmares (DSK) 220
4 Spyglass Siren (LCI) 78
2 Enduring Curiosity (DSK) 51
2 Great Gilded Boat (HOB) 42
2 Bitter Triumph (SOA) 26
2 Shoot the Sheriff (OTJ) 106
2 Tishana's Tidebinder (LCI) 81
1 Spell Pierce (XLN) 81
4 Desolation Prowler (HOB) 64
2 Cecil, Dark Knight (FIN) 91
3 Requiting Hex (ECL) 116
2 Dream Beavers (TMT) 62
4 Floodpits Drowner (DSK) 59
1 Spell Snare (ECL) 71
2 The Wondrous Wasp (MSH) 84
4 Watery Grave (GRN) 259
4 Gloomlake Verge (DSK) 260
2 Soulstone Sanctuary (FDN) 133
2 Restless Reef (LCI) 282
4 Island (ZNR) 381
4 Swamp (ZNR) 382
1 Fountainport (BLB) 253
1 Hidden Lair (MSH) 269
1 Shipwreck Marsh (MID) 267"""


def card(name, cost="{U}", type_line="Creature", **extra):
    return dict(name=name, oracle_id=name, mana_cost=cost, type_line=type_line, layout="normal", **extra)


def response(cards):
    return io.BytesIO(json.dumps({"object": "list", "data": cards}).encode())


class DecklistParsingTests(unittest.TestCase):
    def test_arena_annotations_sections_and_parenthesized_names(self):
        entries = parse_decklist("\nDeck\n2 Kaito, Bane of Nightmares (DSK) 220\n1 B.F.M. (Big Furry Monster)\n"
                                 "\nSideboard\nthis section is excluded\n")
        self.assertEqual([(r.name, r.count, r.line) for r in entries],
                         [("Kaito, Bane of Nightmares", 2, 3), ("B.F.M. (Big Furry Monster)", 1, 4)])

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_parse_errors_are_aggregated_before_network(self, fetch):
        with self.assertRaises(DecklistImportError) as caught:
            import_decklist("0 Island\nmissing quantity\n-1 Swamp")
        self.assertEqual(len(caught.exception.diagnostics), 3)
        self.assertIn("Line 2", str(caught.exception))
        fetch.assert_not_called()
        with self.assertRaisesRegex(DecklistImportError, "empty"):
            parse_decklist("Deck\n\nSideboard\n1 Island")


class ScryfallLookupTests(unittest.TestCase):
    @patch("mtg_tools.decklist_import.sleep")
    @patch("mtg_tools.decklist_import.monotonic", side_effect=[1, 1.2, 1.5])
    @patch("mtg_tools.decklist_import.urlopen")
    def test_batches_deduplicate_headers_timeout_and_spacing(self, open_url, clock, sleep):
        names = [f"Card {n}" for n in range(76)]
        open_url.side_effect = [response([card(name) for name in names[:75]]), response([card(names[75])])]
        self.assertEqual(len(fetch_cards([*names, "CARD 0"])), 76)
        self.assertEqual(open_url.call_count, 2)
        request = open_url.call_args_list[0].args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://api.scryfall.com/cards/collection")
        self.assertEqual(len(json.loads(request.data)["identifiers"]), 75)
        self.assertEqual(request.get_header("User-agent"), "mtg-tools/0.1")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(open_url.call_args.kwargs, {"timeout": 30})
        sleep.assert_called_once()
        self.assertAlmostEqual(sleep.call_args.args[0], 0.3)

    @patch("mtg_tools.decklist_import.urlopen")
    def test_network_http_and_invalid_responses_fail_without_retry(self, open_url):
        failures = [URLError("offline"), TimeoutError("timed out"),
                    HTTPError("https://api.scryfall.com", 429, "Too Many Requests", {}, None)]
        for failure in failures:
            with self.subTest(failure=failure):
                open_url.reset_mock()
                open_url.side_effect = failure
                with self.assertRaises(DecklistImportError):
                    fetch_cards(["Island"])
                open_url.assert_called_once()
        open_url.side_effect = None
        for payload in (b"invalid json", b"{}", b'{"object":"list","data":[{}]}'):
            with self.subTest(payload=payload):
                open_url.return_value = io.BytesIO(payload)
                with self.assertRaises(DecklistImportError):
                    fetch_cards(["Island"])

    @patch("mtg_tools.decklist_import.urlopen", side_effect=lambda *args, **kwargs: response([card("Spyglass Siren")]))
    def test_imports_make_fresh_requests(self, open_url):
        import_decklist("1 Spyglass Siren")
        import_decklist("1 Spyglass Siren")
        self.assertEqual(open_url.call_count, 2)


class SpellConversionTests(unittest.TestCase):
    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_reordered_response_duplicates_format_and_evaluator_input(self, fetch):
        fetch.return_value = [card("Bitter Triumph", "{1}{B}"), card("Island", "", "Basic Land — Island"),
                              card("Kaito, Bane of Nightmares", "{2}{U}{B}"), card("Spyglass Siren")]
        imported = import_decklist("4 Kaito, Bane of Nightmares (DSK) 220\n2 Bitter Triumph (SOA) 26\n"
                                   "1 Island\n4 Spyglass Siren\n1 BITTER TRIUMPH (LCI) 91")
        self.assertEqual(imported.spells, (SpellCost("2UB", 4), SpellCost("1B", 3), SpellCost("U", 4)))
        self.assertEqual([r.name for r in imported.rows],
                         ["Kaito, Bane of Nightmares", "Bitter Triumph", "Spyglass Siren"])
        self.assertEqual(imported.excluded_land_count, 1)
        namespace = {"SpellCost": SpellCost}
        exec(format_spells(imported), namespace)
        self.assertEqual(namespace["SPELLS"], imported.spells)
        self.assertIn("# Kaito, Bane of Nightmares", format_spells(imported))
        count, costs, weights = spell_components(imported.spells)
        self.assertEqual(count, 11)
        self.assertEqual(costs, {"2UB": 4, "1B": 3, "U": 4})
        self.assertEqual(costs, weights)

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_simple_generic_zero_and_same_cost_different_names(self, fetch):
        fetch.return_value = [card("First", "{B}{2}{U}"), card("Second", "{2}{U}{B}"),
                              card("Free", "{0}"), card("Large", "{12}")]
        imported = import_decklist("1 First\n2 Second\n3 Free\n4 Large")
        self.assertEqual(imported.spells, (SpellCost("2UB", 1), SpellCost("2UB", 2),
                                          SpellCost("0", 3), SpellCost("12", 4)))

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_front_faces_only_and_duplicates_by_oracle_identity(self, fetch):
        for layout in ("transform", "modal_dfc", "adventure", "flip"):
            with self.subTest(layout=layout):
                fetch.return_value = [dict(name="Front // Back", oracle_id="same", layout=layout, card_faces=[
                    {"name": "Front", "mana_cost": "{B}", "type_line": "Creature"},
                    {"name": "Back", "mana_cost": "{X}{B}", "type_line": "Creature"},
                ])]
                imported = import_decklist("2 Front\n3 Front // Back")
                self.assertEqual(imported.spells, (SpellCost("B", 5),))
                self.assertEqual(imported.rows[0].name, "Front")
                with self.assertRaisesRegex(DecklistImportError, "no exact"):
                    import_decklist("1 Back")

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_unsupported_costs_and_unresolved_names_reported_together(self, fetch):
        costs = ("{X}{U}", "{W/U}", "{B/P}", "{S}", "{C}", "", "{U}junk")
        fetch.return_value = [card(f"Unsupported {i}", cost) for i, cost in enumerate(costs)]
        text = "\n".join(f"1 Unsupported {i}" for i in range(len(costs))) + "\n2 Unknown Name"
        with self.assertRaises(DecklistImportError) as caught:
            import_decklist(text)
        self.assertEqual(len(caught.exception.diagnostics), 8)
        self.assertIn("Unknown Name", str(caught.exception))
        self.assertIn("not a zero-cost", str(caught.exception))

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_unsupported_multiface_and_missing_types(self, fetch):
        fetch.return_value = [dict(name="Fire // Ice", oracle_id="split", layout="split", mana_cost="{2}{U}{R}"),
                              dict(name="Strange", oracle_id="strange", layout="unknown",
                                   card_faces=[{"name": "Strange"}]),
                              card("Untyped", type_line="")]
        with self.assertRaises(DecklistImportError) as caught:
            import_decklist("1 Fire // Ice\n1 Strange\n1 Untyped")
        self.assertEqual(len(caught.exception.diagnostics), 3)

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_front_land_is_excluded_even_with_spell_back(self, fetch):
        fetch.return_value = [dict(name="Land // Spell", oracle_id="mdfc", layout="modal_dfc", card_faces=[
            {"name": "Land", "type_line": "Land", "mana_cost": ""},
            {"name": "Spell", "type_line": "Sorcery", "mana_cost": "{U}"},
        ])]
        imported = import_decklist("2 Land")
        self.assertEqual(imported.spells, ())
        self.assertEqual(imported.excluded_land_count, 2)
        namespace = {}
        exec(format_spells(imported), namespace)
        self.assertEqual(namespace["SPELLS"], ())

    @patch("mtg_tools.decklist_import.fetch_cards")
    def test_supplied_deck_counts_and_all_land_families_excluded(self, fetch):
        entries = parse_decklist(SAMPLE_DECK)
        self.assertEqual(sum(e.count for e in entries), 60)
        # Synthetic costs test routing/counts, not the live printed costs of these cards.
        fetch.return_value = [card(entry.name, "{U}" if i < 15 else "", "Creature" if i < 15 else "Land")
                              for i, entry in reversed(list(enumerate(entries)))]
        imported = import_decklist(SAMPLE_DECK)
        self.assertEqual(len(imported.rows), 15)
        self.assertEqual(sum(spell.count for spell in imported.spells), 37)
        self.assertEqual(imported.excluded_land_count, 23)


if __name__ == "__main__":
    unittest.main()
