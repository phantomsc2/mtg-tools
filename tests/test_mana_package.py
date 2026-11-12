"""Regression checks for serialized evaluation state across the module split."""

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
    def test_legacy_cache_module_paths_restore_without_recomputation(self):
        source = ManaSource("U", "basic")
        space = ManaSpace({source: (0, 2)}, 2)
        spells = (SpellCost("U", 2),)
        model = heuristic_mana_model()
        evaluator = LocalManaEvaluator(space, spells, model=model, turns=2)
        expected = evaluator.value({source: 2})
        payload = pickle.dumps((evaluator.cache_signature, dict(evaluator.cache)), protocol=0)
        # Protocol zero names globals explicitly, allowing a fixture using the
        # previous module paths without modifying runtime class identities.
        for current, previous in [
            (b"mtg_tools.mana.lands\n", b"mtg_tools.mana_lands\n"),
            (b"mtg_tools.mana.model\n", b"mtg_tools.mana_model\n"),
            (b"mtg_tools.mana.spells\n", b"mtg_tools.mana_opportunities\n"),
            (b"mtg_tools.mana.evaluation\n", b"mtg_tools.mana_opportunities\n"),
        ]:
            payload = payload.replace(current, previous)
        signature, entries = pickle.loads(payload)
        self.assertTrue(all(isinstance(value, OpportunityResult) for value in entries.values()))
        restored = LocalManaEvaluator(space, spells, model=model, turns=2)
        restored.restore_cache(signature, entries)
        with patch("mtg_tools.mana.evaluation.evaluate", side_effect=AssertionError("cache miss")):
            self.assertEqual(restored.value({source: 2}), expected)

    def test_legacy_ranked_result_resolves_to_new_type(self):
        expected = RankedBase((2, 0), Fraction(1, 3), None, None)
        payload = pickle.dumps(expected, protocol=0).replace(
            b"mtg_tools.mana.evaluation\n", b"mtg_tools.mana_search\n"
        )
        restored = pickle.loads(payload)
        self.assertIs(type(restored), RankedBase)
        self.assertEqual(restored, expected)
