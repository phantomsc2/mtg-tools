import unittest
from collections import Counter
from fractions import Fraction

from mana_analysis import Mode, probability
from mana_dual_search import BASES, event_weights


class DualSearchTests(unittest.TestCase):
    def test_scalar_agreement(self):
        self.assertEqual(len(BASES), 378)
        counts = (12, 8, 6)
        deck = Counter(dict(zip(("Watery Grave", "Overgrown Tomb", "Breeding Pool"), counts)))
        deck.update(target=4, other=30)
        for total, colored in ((2, "GG"), (3, "BGU"), (4, "BBUU"), (4, "BUWW"), (9, "UU")):
            weights, denominator = event_weights(total, colored, 4, total+6)
            value, numerator, conditioning = probability(deck, Mode("target", "test", total-len(colored), colored), total+6)
            self.assertEqual((int(weights[BASES.index(counts)]), denominator), (numerator, conditioning))
            self.assertEqual(Fraction(numerator, denominator), value)


if __name__ == "__main__":
    unittest.main()
