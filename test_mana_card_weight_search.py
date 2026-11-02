import unittest
from fractions import Fraction as F

from mana_card_weight_search import first_transition, nearby_weight


class CardWeightTransitionTests(unittest.TestCase):
    def test_first_envelope_change(self):
        self.assertEqual(first_transition([(10, 1), (8, 2), (0, 4)]), (0, 1, F(2), F(4)))

    def test_simultaneous_crossing_selects_right_hand_winner(self):
        self.assertEqual(first_transition([(10, 0), (9, 1), (8, 2)], F(0)), (0, 2, F(1), None))

    def test_no_transition(self):
        with self.assertRaises(ValueError):
            first_transition([(10, 2), (8, 1)])

    def test_nearby_coefficient_is_strictly_in_interval(self):
        lower, upper = F("1.00001"), F("1.00002")
        weight = nearby_weight(lower, upper)
        self.assertTrue(lower < weight < upper)

    def test_cli_weight_configuration(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from click.testing import CliRunner
        from mana_card_weight_search import main

        runner = CliRunner()
        with TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            config.write_text(json.dumps({"weight": "1.1", "penalty": "0.0032"}))
            with patch("mana_card_weight_search.search") as calculate:
                result = runner.invoke(main, ["--config", str(config), "--weight", "1.2"])
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(calculate.call_args.args[:2], (F("0.0032"), F("1.2")))
