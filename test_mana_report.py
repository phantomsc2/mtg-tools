import json
import unittest
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from click.testing import CliRunner

from mana_analysis import ROOT, read_deck
from mana_report import main, revise_deck, suggestion_text, validate_deck


class ReportTests(unittest.TestCase):
    def test_physical_spell_swap_preserves_sixty(self):
        original = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
        revised = revise_deck(original, {"Awaken the Honored Dead": -1, "Bitter Triumph": 1})
        self.assertEqual((sum(revised.values()), revised["Awaken the Honored Dead"], revised["Bitter Triumph"]),
                         (60, 2, 4))
        self.assertEqual(original["Awaken the Honored Dead"], 3)
        for changes in ({"Awaken the Honored Dead": -1}, {"Awaken the Honored Dead": -4},
                        {"Bitter Triumph": 2, "Awaken the Honored Dead": -2}, {"Swamp": 1}):
            with self.assertRaises(ValueError):
                revise_deck(original, changes)

    def test_deck_validation(self):
        for deck in (Counter({"Swamp": 60}), Counter({"Swamp": 26, "Moonshadow": 33}),
                     Counter({"Swamp": 26, "Moonshadow": 34})):
            with self.assertRaises(ValueError):
                validate_deck(deck)

    def test_report_suggestion_has_gain_and_cost(self):
        entry = dict(status="crossing", multiplier=F(11, 10),
                     swap={"out": {"A": 2}, "in": {"B": 2}},
                     delta_target=F(1, 100), baseline_cost=F(1, 10000))
        text = suggestion_text(entry, "more")
        self.assertIn("OUT: 2 A", text)
        self.assertIn("IN: 2 B", text)
        self.assertIn("+1.000000 pp", text)
        self.assertIn("+0.010000 pp", text)
        self.assertIn("zero", suggestion_text({"status": "no_crossing"}, "less"))

    def test_config_and_cli_precedence(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text(json.dumps(dict(deck=str(ROOT / "resources/decks/evoke_elementals.txt"),
                                           changes={"Awaken the Honored Dead": -1, "Bitter Triumph": 1},
                                           weights={"Awaken the Honored Dead": "1.1"}, penalty="0.0032",
                                           output="result")))
            with patch("mana_report.build_report") as build:
                result = CliRunner().invoke(main, ["--config", str(path), "--penalty", "0.004"])
                self.assertEqual(result.exit_code, 0, result.output)
                args = build.call_args.args
                self.assertEqual(args[1], {"Awaken the Honored Dead": -1, "Bitter Triumph": 1})
                self.assertEqual(args[2], {"Awaken the Honored Dead": F(11, 10)})
                self.assertEqual(args[3], F("0.004"))
                self.assertEqual(args[4], path.parent / "result")
