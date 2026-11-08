import unittest
from fractions import Fraction

from examples.sultai_shock_sweep import penalty_intervals


class ShockThresholdTests(unittest.TestCase):
    def test_upper_envelope_skips_dominated_and_preserves_ties(self):
        rows = [{'shocks': 8, 'exact_raw': '3'},
                {'shocks': 9, 'exact_raw': '3.01'},
                {'shocks': 10, 'exact_raw': '3.04'}]
        intervals = penalty_intervals(rows)
        self.assertEqual(Fraction(intervals[0]['lower']), Fraction('0.02'))
        self.assertIsNone(intervals[0]['upper'])
        self.assertIsNone(intervals[1])
        self.assertEqual(Fraction(intervals[2]['upper']), Fraction('0.02'))
        for p in (Fraction(0), Fraction('.02'), Fraction('.03')):
            best = max(Fraction(r['exact_raw'])-r['shocks']*p for r in rows)
            for row, interval in zip(rows, intervals):
                if interval is not None and Fraction(interval['lower']) <= p and (
                        interval['upper'] is None or p <= Fraction(interval['upper'])):
                    self.assertEqual(Fraction(row['exact_raw'])-row['shocks']*p, best)
