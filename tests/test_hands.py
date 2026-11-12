import unittest
from collections import Counter
from itertools import combinations
from math import comb, fsum
from random import Random

from mtg_tools.hands import Card, compositions, expected_score, hand_distribution
from mtg_tools.search import BudgetExhausted, DeckSpace, Objective, optimize


class ExactHandsTests(unittest.TestCase):
    def test_physical_card_enumeration(self):
        physical = "aaabbc"
        observed = Counter(tuple(sorted(physical[i] for i in indices)) for indices in combinations(range(6), 3))
        distribution = list(hand_distribution(Counter(physical), 3))
        self.assertAlmostEqual(fsum(p for _, p in distribution), 1)
        for hand, probability in distribution:
            self.assertAlmostEqual(probability, observed[tuple(sorted(hand.elements()))] / comb(6, 3))

    def test_known_expectations(self):
        deck = {"land": 24, "spell": 36}
        self.assertAlmostEqual(expected_score(deck, lambda h: 5), 5)
        self.assertAlmostEqual(expected_score(deck, lambda h: h["land"]), 7 * 24 / 60)
        self.assertAlmostEqual(expected_score(deck, lambda h: h["land"] == 0), comb(36, 7) / comb(60, 7))
        self.assertEqual(expected_score({}, lambda h: len(h), 0), 0)

    def test_invalid_inputs(self):
        for deck, size in [({"a": 1.5}, 1), ({"a": -1}, 0), ({"a": 2}, 3)]:
            with self.assertRaises(ValueError):
                expected_score(deck, lambda h: 1, size)
        with self.assertRaises(ValueError):
            expected_score({"a": 1}, lambda h: float("nan"), 1)

    def test_integer_projection(self):
        space = DeckSpace(("a", "b", "c"), (1, 2, 0), (3, 7, 9), 12)
        rng = Random(2)
        for logits in [(0, 0, 0), (10000, -10000, 0)] + [tuple(rng.uniform(-50, 50) for _ in range(3))
                                                        for _ in range(100)]:
            self.assertEqual(sum(space.decode(logits)), 12)
        tied = DeckSpace(("a", "b", "c"), (0, 0, 0), (4, 4, 4), 4)
        self.assertEqual(tied.decode((0, 0, 0)), (2, 1, 1))

    def test_ordered_cache_and_budget(self):
        objective = Objective(DeckSpace(("a", "b"), (0, 0), (4, 4), 4), lambda h: h["a"], 2, 1)
        self.assertNotEqual(objective((1, 3)), objective((3, 1)))
        objective((1, 3))
        self.assertEqual(len(objective.cache), 2)
        with self.assertRaises(BudgetExhausted):
            objective((2, 2))

    def test_multiple_roles_are_one_card(self):
        card = Card("flexible", 2, frozenset({"threat", "removal"}))
        self.assertEqual(expected_score({card: 4}, lambda h: sum(h.values()), 2), 2)

    def test_fixed_space_terminates(self):
        space = DeckSpace(("a", "b"), (2, 2), (2, 2), 4)
        result = optimize(Objective(space, lambda h: 1, 10, 2), (2, 2), max_proposals=10)
        self.assertEqual(result.evaluations, 1)
        self.assertEqual(result.stopped, "proposal limit")

    def test_search_against_exhaustive_optimum(self):
        space = DeckSpace(("a", "b"), (0, 0), (6, 6), 6)
        score = lambda h: h["a"]
        optimum = max(expected_score(dict(zip(space.cards, d)), score, 2) for d in compositions(space.maximum, 6))
        for seed in (0, 1, 2):
            objective = Objective(space, score, 7, 2)
            result = optimize(objective, (3, 3), seed=seed, max_proposals=500)
            self.assertAlmostEqual(result.score, optimum)
            self.assertLessEqual(result.evaluations, 7)


if __name__ == "__main__":
    unittest.main()
