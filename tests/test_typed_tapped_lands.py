import unittest
from fractions import Fraction as F

from mtg_tools.mana.lands import ManaSource as S, sources_for_colors
from mtg_tools.mana.policy import land_availability
from mtg_tools.mana.policy import heuristic_mana_model
from mtg_tools.mana.spells import SpellCost
from mtg_tools.mana.evaluation import evaluate
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.tables import build_component_table
from test_land_availability import physical_oracle


MODEL = heuristic_mana_model()


class TypedTappedLandTests(unittest.TestCase):
    def test_validation_and_inferred_types(self):
        dual = S('BU', 'typed_tapped')
        self.assertEqual(dual, S('UB', 'typed_tapped', 'BU'))
        self.assertEqual((dual.colors, dual.types), ('UB', 'UB'))
        for colors in ('U', 'UBG', 'UU', 'UX', None):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                S(colors, 'typed_tapped')
        for types in ('U', 'B', 'UG', 'UBG', 'UUB', None):
            with self.subTest(types=types), self.assertRaises(ValueError):
                S('UB', 'typed_tapped', types)
        self.assertEqual(S('UB', 'tapped').types, '')
        with self.assertRaises(ValueError):
            S('UB', 'tapped', 'UB')

    def test_pool_generation_and_standard_snapshot(self):
        for format in (None, 'standard'):
            all_pairs = sources_for_colors('WUBRG', ['typed_tapped'], format=format)
            self.assertEqual(len(all_pairs), 10)
            self.assertTrue(all(s.types == s.colors for s in all_pairs))
            sultai = ManaSpace.from_colors(2, 'GBU', format=format,
                                          families={'typed_tapped': (0, 2)})
            self.assertEqual(set(sultai.sources), {S(p, 'typed_tapped') for p in ('UB', 'UG', 'BG')})
            self.assertEqual(sources_for_colors('U', ['typed_tapped'], format=format), ())

    def test_availability_and_single_mana(self):
        self.assertEqual([land_availability('typed_tapped', t) for t in range(1, 5)],
                         [F(0), F(1, 2), F(2, 3), F(3, 4)])
        for cost in ('U', 'B', 'UB'):
            typed = evaluate({S('UB', 'typed_tapped'): 1}, [SpellCost(cost, 1)],
                             model=MODEL, turns=3, opening_hand_size=99)
            untyped = evaluate({S('UB', 'tapped'): 1}, [SpellCost(cost, 1)],
                               model=MODEL, turns=3, opening_hand_size=99)
            self.assertEqual(typed, untyped)
            if cost == 'UB':
                self.assertTrue(all(row.expected_copies == 0 for row in typed.opportunities))

    def test_unavailable_typed_land_enables_verge(self):
        for kind, expected in (('typed_tapped', F(1)), ('tapped', F(0))):
            base = {S('UB', kind): 1, S('UB', 'verge'): 1}
            result = evaluate(base, [SpellCost('B', 1)], model=MODEL,
                              turns=1, opening_hand_size=99)
            self.assertTrue(all(row.expected_copies == expected for row in result.opportunities))

    def test_physical_draw_oracle_and_backend_parity(self):
        base = {S('BG', 'typed_tapped'): 1, S('UB', 'verge'): 1,
                S('UG', 'shock', 'UG'): 1}
        spells = [SpellCost(c, 1) for c in ('BG', 'UU', 'B')]
        result = evaluate(base, spells, model=MODEL, turns=3, opening_hand_size=2)
        for row in result.opportunities:
            seen = min(6, 2 + row.turn - (row.position == 'play'))
            self.assertEqual(row.expected_copies,
                             physical_oracle(base, spells, seen, row.turn).get(row.cost, 0))
        space = ManaSpace({s: (0, 2) for s in base}, 3)
        args = dict(turns=3, opening_hand_size=2)
        scalar = build_component_table(space, spells, model=MODEL, backend='scalar', **args)
        batch = build_component_table(space, spells, model=MODEL, backend='batch', **args)
        self.assertEqual(scalar, batch)
        self.assertEqual(scalar.rank(), batch.rank())

    def test_independent_family_limits(self):
        a, b, untyped = S('UB', 'typed_tapped'), S('UG', 'typed_tapped'), S('UB', 'tapped')
        space = ManaSpace({s: (0, 2) for s in (a, b, untyped)}, 2,
                          family_bounds={'typed_tapped': (1, 1), 'tapped': (1, 1)})
        self.assertEqual(space.candidate_count(), 2)
        self.assertEqual(len(tuple(space.exhaustive())), 2)
        space.counts({a: 1, untyped: 1})
        with self.assertRaises(ValueError):
            space.counts({a: 1, b: 1})
        with self.assertRaises(ValueError):
            space.counts({untyped: 2})


if __name__ == '__main__':
    unittest.main()
