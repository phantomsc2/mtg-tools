import unittest
from collections import Counter
from fractions import Fraction
from itertools import product
from math import comb

import numpy as np

from mana_analysis import LANDS, Mode, can_pay, probability
from mana_search import NAMES, binomial_transform, event_weights, feasible_draws


class ManaSearchTests(unittest.TestCase):
    def test_binomial_transform(self):
        values = np.arange(12, dtype=np.int64).reshape(3, 4)
        result = binomial_transform(values)
        for a, b in product(range(3), range(4)):
            expected = sum(comb(a, i)*comb(b, j)*int(values[i, j])
                           for i in range(a+1) for j in range(b+1))
            self.assertEqual(result[a, b], expected)

    def test_feasible_upward_closure(self):
        flags = feasible_draws(2, "BB", True)
        lands = tuple(LANDS[n] for n in NAMES)
        for counts in [(1, 0, 0, 0, 2, 0, 0, 0, 0),
                       (0, 0, 0, 1, 2, 0, 0, 0, 0),
                       (0, 0, 0, 0, 0, 0, 0, 1, 1),
                       (1, 2, 2, 2, 2, 2, 2, 2, 2)]:
            self.assertEqual(bool(flags[counts]), can_pay(lands, counts, 2, "BB", True))

    def test_against_scalar_exact_evaluator(self):
        counts = (1, 4, 4, 4, 3, 3, 3, 2, 2)
        deck = Counter(dict(zip(NAMES, counts)))
        deck.update({"target": 4, "other": 30})
        for mode in (Mode("target", "test", 0, "BB"), Mode("target", "test", 0, "BGU", False)):
            weights, denominator = event_weights(mode.total, mode.colored, mode.creature, 4, mode.total+6)
            expected, numerator, conditioning = probability(deck, mode, mode.total+6)
            self.assertEqual(int(weights[counts]), numerator)
            self.assertEqual(denominator, conditioning)
            self.assertEqual(Fraction(int(weights[counts]), denominator), expected)

    def test_fifth_copy_capacity(self):
        counts = (1, 5, 4, 4, 3, 3, 2, 2, 2)
        deck = Counter(dict(zip(NAMES, counts)))
        deck.update({"target": 4, "other": 30})
        mode = Mode("target", "test", 0, "BGU", False)
        weights, denominator = event_weights(3, "BGU", False, 4, 9, capacities=counts)
        expected, numerator, conditioning = probability(deck, mode, 9)
        self.assertEqual((int(weights[counts]), denominator), (numerator, conditioning))
        self.assertEqual(Fraction(numerator, denominator), expected)


if __name__ == "__main__":
    unittest.main()
