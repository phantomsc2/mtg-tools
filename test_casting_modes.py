import unittest
from fractions import Fraction

from mana_opportunities import CastingMode, ManaSource, Spell, SpellCost, evaluate
from mana_search import ManaSpace, build_component_table


class CastingModeTests(unittest.TestCase):
    def test_single_mode_is_identical(self):
        base = {ManaSource("U", "basic"): 3}
        old = [SpellCost("UU", 4, 2)]
        new = [Spell(4, (CastingMode("UU"),), 2)]
        self.assertEqual(evaluate(base, old), evaluate(base, new))

    def test_physical_counts_and_uniform_average(self):
        base = {ManaSource("U", "basic"): 2}
        spells = [Spell(2, (CastingMode("UU"), CastingMode("BB")))]
        result = evaluate(base, spells, turns=2, opening_hand_size=2, position="play")
        uu = next(r for r in result.opportunities if r.cost == "UU" and r.turn == 2)
        # Three cards seen from four: two successful hands, one spell each.
        self.assertEqual(uu.expected_copies, Fraction(1, 4))
        self.assertEqual(result.raw_score, 1 / 8)

    def test_weighted_modes_and_search(self):
        u, b = ManaSource("U", "basic"), ManaSource("B", "basic")
        spells = [Spell(3, (CastingMode("U", 3), CastingMode("B", 1)), 2), SpellCost("B", 1)]
        space = ManaSpace({u: (0, 2), b: (0, 2)}, 2)
        table = build_component_table(space, spells, opening_hand_size=2)
        for row in table.rank():
            result = evaluate(dict(zip(space.sources, row.counts)), spells, opening_hand_size=2)
            self.assertAlmostEqual(float(row.score), result.score)
        table.crossings("U")

    def test_invalid_modes(self):
        for modes in ((), (CastingMode("U", 0),)):
            with self.assertRaises(ValueError):
                Spell(2, modes)


if __name__ == "__main__":
    unittest.main()
