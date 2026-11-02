import unittest
from fractions import Fraction as F

from mana_sensitivity import land_swap, next_crossing, optimal_interval, winner_at


class SensitivityTests(unittest.TestCase):
    def test_both_directions(self):
        lines = [(10, 1), (8, 2), (0, 4), (F(21, 2), 0)]
        bases = [(2, 0), (1, 1), (0, 2), (0, 2)]
        up = next_crossing(lines, bases, 0, 1, ("A", "B"))
        down = next_crossing(lines, bases, 0, -1, ("A", "B"))
        self.assertEqual((up.multiplier, up.successor, up.lower, up.upper), (F(2), 1, F(2), F(4)))
        self.assertEqual((down.multiplier, down.successor, down.lower, down.upper), (F(1, 2), 3, F(0), F(1, 2)))

    def test_simultaneous_crossings_and_swap_tie_break(self):
        # At x=2 all four lines meet. Highest right-hand slope wins; among
        # identical winning lines choose the one requiring fewer replacements.
        lines = [(4, 0), (2, 1), (0, 2), (0, 2)]
        bases = [(4, 0, 0), (3, 1, 0), (0, 0, 4), (3, 0, 1)]
        up = next_crossing(lines, bases, 0, 1, ("A", "B", "C"))
        self.assertEqual((up.multiplier, up.successor), (F(2), 3))

    def test_current_tie_and_identical_lines(self):
        lines, bases = [(1, 0), (0, 1)], [(1, 0), (0, 1)]
        up = next_crossing(lines, bases, 0, 1, ("A", "B"))
        self.assertEqual((up.status, up.multiplier, up.successor), ("already_tied", F(1), 1))
        self.assertIsNone(next_crossing([(1, 0), (1, 0)], bases, 0, 1, ("A", "B")))

    def test_nonnegative_boundary_and_no_flip(self):
        down = next_crossing([(0, 1), (0, 0)], [(1, 0), (0, 1)], 0, -1, ("A", "B"))
        self.assertEqual((down.status, down.multiplier), ("boundary_tie", F(0)))
        self.assertIsNone(next_crossing([(1, 1), (0, 0)], [(1, 0), (0, 1)], 0, -1, ("A", "B")))

    def test_interval_and_invalid_baseline(self):
        self.assertEqual(optimal_interval([(10, 1), (8, 2), (0, 4)], 1), (F(2), F(4)))
        self.assertEqual(winner_at([(10, 1), (8, 2), (0, 4)], F(3)), [1])
        with self.assertRaises(ValueError):
            next_crossing([(10, 1), (8, 2)], [(1, 0), (0, 1)], 1, 1, ("A", "B"))

    def test_multi_land_swap_and_size_validation(self):
        result = land_swap((13, 13, 0), (10, 12, 4), ("A", "B", "C"))
        self.assertEqual(result, {"out": {"A": 3, "B": 1}, "in": {"C": 4}, "cards_replaced": 4})
        with self.assertRaises(ValueError):
            land_swap((13, 13), (12, 13), ("A", "B"))
