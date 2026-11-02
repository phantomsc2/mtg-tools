import unittest
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import comb

from hands import hand_weights
from mana_analysis import LANDS, ROOT, Land, Mode, can_pay, casting_modes, percentage, probability, read_deck


class ManaTests(unittest.TestCase):
    def test_integer_weights(self):
        physical = "aaabbc"
        observed = Counter(tuple(sorted(physical[i] for i in indices))
                           for indices in combinations(range(6), 3))
        weights = list(hand_weights(Counter(physical), 3))
        self.assertEqual(sum(w for _, w in weights), comb(6, 3))
        for hand, weight in weights:
            self.assertEqual(weight, observed[tuple(sorted(hand.elements()))])
        for deck, size in [({"a": -1}, 0), ({"a": 1.5}, 1), ({"a": 1}, 2)]:
            with self.assertRaises(ValueError):
                list(hand_weights(deck, size))

    def test_conditional_probability_against_physical_draws(self):
        deck = Counter({"Swamp": 2, "Breeding Pool": 2, "target": 2, "other": 2})
        mode = Mode("target", "test", 0, "BB")
        physical = list(deck.elements())
        successful = conditioned = 0
        for indices in combinations(range(8), 5):
            hand = Counter(physical[i] for i in indices)
            if hand["target"] and hand["Swamp"] + hand["Breeding Pool"] >= 2:
                conditioned += 1
                successful += hand["Swamp"] == 2
        value, success, denominator = probability(deck, mode, 5)
        self.assertEqual((success, denominator), (successful, conditioned))
        self.assertEqual(value, Fraction(successful, conditioned))
        self.assertEqual(probability(Counter({"Swamp": 2, "target": 0}), mode, 2), (None, 0, 0))

    def test_land_rules(self):
        cavern = (LANDS["Cavern of Souls"],)
        self.assertTrue(can_pay(cavern, (2,), 2, "WW", True))
        self.assertFalse(can_pay(cavern, (2,), 2, "B", False))
        self.assertTrue(can_pay(cavern, (2,), 2, "", False))
        verge = LANDS["Gloomlake Verge"]
        self.assertFalse(can_pay((verge,), (2,), 2, "BB", True))
        self.assertTrue(can_pay((verge, LANDS["Watery Grave"]), (1, 1), 2, "BB", True))
        self.assertTrue(can_pay((verge, LANDS["Swamp"]), (2, 1), 2, "UB", False))
        # An unchosen typed land cannot activate two Verges on a two-land battlefield.
        self.assertFalse(can_pay((verge, LANDS["Breeding Pool"]), (2, 1), 2, "BB", True))
        self.assertFalse(can_pay((Land("UG"), Land("B")), (1, 1), 2, "UG", True))
        self.assertTrue(can_pay((Land("UG"),), (4,), 4, "UUGG", True))
        both_effects = (LANDS["Starting Town"],)
        self.assertTrue(can_pay(both_effects, (5,), 5, "GGUU", True))
        self.assertTrue(can_pay(both_effects, (5,), 5, "GG", True))
        self.assertTrue(can_pay(both_effects, (5,), 5, "UU", True))

    def test_matching_against_assignments(self):
        lands = (Land("UB"), Land("UG"), Land("B"))
        for counts in product(range(3), repeat=3):
            physical = [land.colors for land, n in zip(lands, counts) for _ in range(n)]
            for requirement in ("BB", "UG", "UBG", "UUGG"):
                total = len(requirement)
                expected = any(all(assignment.count(c) >= requirement.count(c) for c in set(requirement))
                               for selected in combinations(physical, total) for assignment in product(*selected))
                self.assertEqual(can_pay(lands, counts, total, requirement, True), expected)

    def test_later_turn_unused_land_enables_verges(self):
        lands = (LANDS["Gloomlake Verge"], LANDS["Breeding Pool"])
        self.assertFalse(can_pay(lands, (2, 1), 2, "BB", True, 2))
        self.assertTrue(can_pay(lands, (2, 1), 2, "BB", True, 3))
        self.assertFalse(can_pay(lands, (2, 1), 2, "BB", True, 1))
        deck = Counter({"Gloomlake Verge": 2, "Breeding Pool": 1, "target": 1})
        mode = Mode("target", "test", 0, "BB")
        self.assertEqual(probability(deck, mode, 4, 2)[0], Fraction(0))
        self.assertEqual(probability(deck, mode, 4, 3)[0], Fraction(1))

    def test_percentage_display(self):
        self.assertEqual(percentage(Fraction(1)), "100%")
        self.assertEqual(percentage(Fraction(1, 2)), "50%")
        self.assertEqual(percentage(Fraction(1, 3)), "33.3%")
        self.assertEqual(percentage(Fraction(0)), "0%")
        self.assertEqual(percentage(None), "N/A")

    def test_mode_coverage(self):
        modes = casting_modes()
        deck = read_deck(ROOT / "resources/decks/evoke_elementals.txt")
        self.assertEqual(set(deck) - set(LANDS), {m.card for m in modes})
        self.assertEqual([m.cost for m in modes if m.card == "Wistfulness"],
                         ["GG", "UU", "3GG", "3UU", "1GGUU"])
        self.assertEqual([m.cost for m in modes if m.card == "Sunderflock"],
                         ["7UU", "6UU", "2UU", "1UU", "UU"])

    def test_spider_man_elemental_modes(self):
        modes = [m for m in casting_modes() if m.card == "Superior Spider-Man"]
        self.assertEqual([m.cost for m in modes],
                         ["2UB", "1BBU", "1BUU", "BBUU", "1BUU", "BUGG", "1BBU", "BUWW"])
        self.assertTrue(all(m.total == 4 and m.creature for m in modes))
        # A BUGG payment casts Spider-Man and enables Wistfulness's green effect,
        # but does not supply the two blue mana needed for its blue effect.
        lands = (Land("B"), Land("U"), Land("G"))
        self.assertTrue(can_pay(lands, (1, 1, 2), 4, "BUGG", True))
        self.assertFalse(can_pay(lands, (1, 1, 2), 4, "BUU", True))
        self.assertTrue(can_pay((Land("BU"),), (4,), 4, "BBUU", True))
        self.assertTrue(can_pay((Land("BU"),), (4,), 4, "BBU", True))
        self.assertTrue(can_pay((Land("BU"),), (4,), 4, "BUU", True))


if __name__ == "__main__":
    unittest.main()
