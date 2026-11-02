import unittest
from fractions import Fraction as F

from mana_regularization import frontier


class RegularizationTests(unittest.TestCase):
    def test_transition_intervals_and_dominated_option(self):
        self.assertEqual(frontier({3: F(9, 10), 2: F(4, 5), 1: F(3, 4)}),
                         [(3, F(0), F(3, 40)), (1, F(3, 40), None)])

    def test_frontier_optimality(self):
        scores = {4: F(91, 100), 3: F(90, 100), 2: F(88, 100), 1: F(80, 100)}
        for count, low, high in frontier(scores):
            penalty = low+1 if high is None else (low+high)/2
            self.assertTrue(all(scores[count]-penalty*count >= success-penalty*n
                                for n, success in scores.items()))


if __name__ == "__main__":
    unittest.main()
