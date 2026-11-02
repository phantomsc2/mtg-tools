import unittest
from collections import Counter
from fractions import Fraction as F

from mana_analysis import Mode, ROOT, casting_modes, read_deck
from mana_fitness import mode_weights


class FitnessWeightsTests(unittest.TestCase):
    def test_normalization_and_copy_mode_weights(self):
        deck = Counter({"Swamp": 2, "A": 2, "B": 1})
        modes = (Mode("A", "first", 0, "B"), Mode("A", "second", 1, "B"), Mode("B", "only", 0, "B"))
        self.assertEqual([w for _, w in mode_weights(deck, modes)], [F(1, 6)]*3)
        self.assertEqual([w for _, w in mode_weights(deck, modes, {"B": F(2)})], [F(1, 8), F(1, 8), F(1, 4)])
        self.assertEqual(2*sum(w for _, w in mode_weights(deck, modes, {"B": F(2)})), 1)

    def test_actual_deck_weight_and_reduction(self):
        deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
        modes = casting_modes()
        for factor in (F(1), F(11, 10), F(2)):
            weights = mode_weights(deck, modes, {"Awaken the Honored Dead": factor})
            self.assertEqual(2*sum(w for _, w in weights), 1)
            self.assertEqual(2*sum(w for m, w in weights if m.card == "Awaken the Honored Dead"),
                             3*factor/(31+3*factor))
        self.assertEqual(mode_weights(deck, modes), mode_weights(deck, modes, {"Awaken the Honored Dead": F(1)}))

    def test_invalid_weights(self):
        deck = Counter({"Swamp": 1, "A": 1})
        modes = [Mode("A", "only", 0, "B")]
        for weights in ({"A": F(-1)}, {"A": F(0)}, {"Swamp": F(2)}, {"unknown": F(1)}):
            with self.assertRaises(ValueError):
                mode_weights(deck, modes, weights)
