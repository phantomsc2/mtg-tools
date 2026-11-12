"""Regression checks for serialized mana evaluation state."""

import pickle
import unittest
from fractions import Fraction
from unittest.mock import patch

from mtg_tools.mana.evaluation import LocalManaEvaluator, OpportunityResult, RankedBase
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.policy import heuristic_mana_model
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.spells import SpellCost


class ManaPackageTests(unittest.TestCase):
    def test_cache_round_trip_restores_without_recomputation(self):
        source = ManaSource("U", "basic")
        space = ManaSpace({source: (0, 2)}, 2)
        spells = (SpellCost("U", 2),)
        model = heuristic_mana_model()
        evaluator = LocalManaEvaluator(space, spells, model=model, turns=2)
        expected = evaluator.value({source: 2})
        payload = pickle.dumps((evaluator.cache_signature, dict(evaluator.cache)))
        signature, entries = pickle.loads(payload)
        self.assertTrue(all(isinstance(value, OpportunityResult) for value in entries.values()))
        restored = LocalManaEvaluator(space, spells, model=model, turns=2)
        restored.restore_cache(signature, entries)
        with patch("mtg_tools.mana.evaluation.evaluate", side_effect=AssertionError("cache miss")):
            self.assertEqual(restored.value({source: 2}), expected)

    def test_ranked_result_round_trip(self):
        expected = RankedBase((2, 0), Fraction(1, 3), None, None)
        payload = pickle.dumps(expected)
        restored = pickle.loads(payload)
        self.assertIs(type(restored), RankedBase)
        self.assertEqual(restored, expected)
