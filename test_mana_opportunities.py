import unittest
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import comb
from pathlib import Path

from mana_opportunities import ManaSource, SpellCost, evaluate


def physical_expectations(base, spells, seen, turn):
    """Independent oracle: enumerate physical draws and mana assignments."""
    deck = [("land", source.colors, 0) for source, count in base.items() for _ in range(count)]
    deck += [(spell.cost, "", spell.weight) for spell in spells for _ in range(spell.count)]
    successes = Counter()
    weighted = Counter()
    for indices in combinations(range(len(deck)), seen):
        hand = [deck[i] for i in indices]
        lands = [colors for kind, colors, _ in hand if kind == "land"]
        for cost, _, weight in hand:
            if cost == "land":
                continue
            colored = Counter(c for c in cost if c.isalpha())
            generic = int("".join(c for c in cost if c.isdigit()) or 0)
            total = generic + colored.total()
            payable = total <= min(turn, len(lands)) and any(
                all(assignment.count(c) >= needed for c, needed in colored.items())
                for assignment in product(*lands)
            )
            if payable:
                successes[cost] += 1
                weighted[cost] += weight
    denominator = comb(len(deck), seen)
    return {cost: Fraction(n, denominator) for cost, n in successes.items()}, {
        cost: n / denominator for cost, n in weighted.items()
    }


class ManaOpportunityTests(unittest.TestCase):
    def test_against_physical_draws(self):
        base = {ManaSource("U", "basic"): 1, ManaSource("BU", "dual"): 1,
                ManaSource("WUBRG", "rainbow"): 1}
        spells = [SpellCost("UU", 2, 1.5), SpellCost("1B", 1), SpellCost("BU", 1, 0),
                  SpellCost("2", 1), SpellCost("0", 1, 0.5)]
        for opening in (0, 2, 7, 20):
            result = evaluate(base, spells, opening_hand_size=opening, turns=3)
            for row in result.opportunities:
                seen = min(9, opening + row.turn - (row.position == "play"))
                expected, weighted = physical_expectations(base, spells, seen, row.turn)
                self.assertEqual(row.expected_copies, expected.get(row.cost, 0), row)
                self.assertAlmostEqual(row.weighted_contribution, weighted.get(row.cost, 0), msg=str(row))
            self.assertAlmostEqual(result.raw_score, sum(r.weighted_contribution for r in result.opportunities) / 6)

    def test_copies_and_incompatible_land_selections_score_independently(self):
        base = {ManaSource("U", "basic"): 2, ManaSource("B", "basic"): 2}
        result = evaluate(base, [SpellCost("UU", 2), SpellCost("BB", 2)],
                          turns=2, opening_hand_size=8, position="play")
        self.assertEqual([r.expected_copies for r in result.opportunities], [0, 2, 0, 2])
        self.assertEqual(result.raw_score, 2)

    def test_source_assignment_and_generic_mana(self):
        cases = [({ManaSource("UB", "dual"): 1}, "UB", 0),
                 ({ManaSource("UB", "dual"): 2}, "UB", 1),
                 ({ManaSource("UB", "dual"): 2}, "UU", 1),
                 ({ManaSource("WUBRG", "rainbow"): 1, ManaSource("G", "basic"): 1}, "UB", 0),
                 ({ManaSource("WUBRG", "rainbow"): 1, ManaSource("G", "basic"): 1}, "1B", 1),
                 ({ManaSource("G", "basic"): 2}, "2", 1)]
        for base, cost, expected in cases:
            with self.subTest(base=base, cost=cost):
                result = evaluate(base, [SpellCost(cost, 1)], turns=2, opening_hand_size=20)
                self.assertEqual(result.opportunities[-1].expected_copies, expected)

    def test_shortage_and_target_draw_remain_in_denominator(self):
        base = {ManaSource("U", "basic"): 1}
        result = evaluate(base, [SpellCost("U", 2)], turns=1, opening_hand_size=2, position="play")
        self.assertEqual(result.opportunities[0].expected_copies, Fraction(2, 3))
        result = evaluate(base, [SpellCost("UU", 2)], turns=7)
        self.assertEqual(result.raw_score, 0)

    def test_weights_do_not_change_draws(self):
        base = {ManaSource("U", "basic"): 2}
        spells = [SpellCost("U", 2), SpellCost("B", 2)]
        unweighted = evaluate(base, spells, opening_hand_size=2)
        scaled = evaluate(base, [SpellCost(s.cost, s.count, 3) for s in spells], opening_hand_size=2)
        self.assertAlmostEqual(scaled.raw_score, 3 * unweighted.raw_score)
        self.assertEqual([r.expected_copies for r in unweighted.opportunities],
                         [r.expected_copies for r in scaled.opportunities])
        zero_weight = evaluate(base, [SpellCost("U", 2), SpellCost("B", 2, 0)], opening_hand_size=2)
        self.assertEqual(unweighted.raw_score, zero_weight.raw_score)
        removed = evaluate(base, [SpellCost("U", 2)], opening_hand_size=2)
        self.assertGreater(removed.raw_score, zero_weight.raw_score)

    def test_equivalent_costs_and_weights_are_aggregated(self):
        base = {ManaSource("BU", "dual"): 2}
        result = evaluate(base, [SpellCost("BU", 1, 2), SpellCost("UB", 2, 0.5)],
                          turns=2, opening_hand_size=20)
        rows = [r for r in result.opportunities if r.turn == 2]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.cost == "UB" and r.expected_copies == 3 and r.weighted_contribution == 3 for r in rows))
        self.assertEqual(SpellCost("0U", 1).cost, "U")
        self.assertEqual(ManaSource("BU", "dual"), ManaSource("UB", "dual"))

    def test_positions_horizon_and_composition_penalty(self):
        base = {ManaSource("U", "basic"): 2, ManaSource("UB", "dual"): 2,
                ManaSource("WUBRG", "rainbow"): 1}
        spells = [SpellCost("U", 5)]
        play = evaluate(base, spells, position="play")
        draw = evaluate(base, spells, position="draw")
        both = evaluate(base, spells, dual_penalty=0.2, rainbow_penalty=0.7)
        self.assertEqual(len(both.opportunities), 14)
        self.assertAlmostEqual(both.raw_score, (play.raw_score + draw.raw_score) / 2)
        self.assertAlmostEqual(both.penalty, 1.1)
        self.assertAlmostEqual(both.score, both.raw_score - 1.1)

    def test_empty_categories_and_unavailable_costs(self):
        base = {ManaSource("U", "basic"): 2}
        self.assertEqual(evaluate(base, []).score, 0)
        self.assertEqual(evaluate(base, [SpellCost("U", 0)]).score, 0)
        self.assertEqual(evaluate({}, [SpellCost("U", 2)]).score, 0)
        self.assertEqual(evaluate({}, [SpellCost("0", 2)]).raw_score, 2)
        result = evaluate(base, [SpellCost("8", 1)])
        self.assertEqual(result.raw_score, 0)

    def test_invalid_inputs(self):
        for cost in ("", "U2", "XU", "{U}", "C", "-1U", "01U", "u", "U/B"):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                SpellCost(cost, 1)
        for colors, kind in (("UU", "dual"), ("U", "dual"), ("C", "basic"),
                             ("UB", "basic"), ("UBG", "rainbow"), ("U", "creature")):
            with self.assertRaises(ValueError):
                ManaSource(colors, kind)
        for count in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                SpellCost("U", count)
            with self.assertRaises(ValueError):
                evaluate({ManaSource("U", "basic"): count}, [])
        for weight in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                SpellCost("U", 1, weight)
            with self.assertRaises(ValueError):
                evaluate({}, [SpellCost("U", 1)], dual_penalty=weight)
        for options in ({"turns": 0}, {"turns": 1.5}, {"opening_hand_size": -1}, {"position": "side"}):
            with self.assertRaises(ValueError):
                evaluate({}, [SpellCost("U", 1)], **options)
        with self.assertRaises(ValueError):
            evaluate({}, [])

    def test_sultai_sample(self):
        from examples.sultai import MANA_BASE, SPELLS

        decklist = Path(__file__).parent / "resources" / "decks" / "evoke_elementals.txt"
        main = decklist.read_text(encoding="utf-8").split("Sideboard")[0].splitlines()
        deck_size = sum(int(line.split()[0]) for line in main if line and line != "Deck")
        self.assertEqual(deck_size, 60)
        self.assertEqual(sum(s.count for s in SPELLS), 34)
        self.assertEqual(sum(MANA_BASE.values()), 26)
        result = evaluate(MANA_BASE, SPELLS)
        self.assertGreater(result.raw_score, 0)
        self.assertTrue(all(r.expected_copies == 0 for r in result.opportunities if r.cost == "7UU"))


if __name__ == "__main__":
    unittest.main()
