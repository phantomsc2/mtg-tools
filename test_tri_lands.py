import unittest
from fractions import Fraction as F
from unittest.mock import patch

from examples.sultai import MANA_BASE, SPELLS
from examples.sultai_optimize import FIXED_LANDS, make_space, optimize, starting_bases
from mana_lands import ManaSource, land_availability, sources_for_colors
from mana_model import heuristic_mana_model
from mana_opportunities import SpellCost, evaluate, spell_components
from mana_search import LocalManaEvaluator, ManaSpace, build_component_table
from test_land_availability import physical_oracle

MODEL = heuristic_mana_model()


class TriLandTests(unittest.TestCase):
    def test_validation_and_filtering(self):
        palace = ManaSource("GBU", "tri")
        self.assertEqual(palace, ManaSource("UBG", "tri"))
        self.assertEqual(palace.types, "")
        for colors in ("UB", "UBGG", "UBX", "WUBRG"):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                ManaSource(colors, "tri")
        with self.assertRaises(ValueError):
            ManaSource("UBG", "tri", types="UBG")
        self.assertEqual(len(sources_for_colors("WUBRG", ["tri"])), 10)
        legal = sources_for_colors("WUBRG", ["tri"], format="standard")
        self.assertEqual({s.colors for s in legal}, {"WUR", "WBR", "WBG", "UBG", "URG"})
        self.assertEqual(sources_for_colors("UBG", ["tri"], format="standard"), (palace,))
        self.assertEqual(sources_for_colors("UBG", ["shock"]),
                         sources_for_colors("UBG", ["shock"], format="standard"))
        self.assertEqual(sources_for_colors("UB", ["tri"]), ())
        with self.assertRaises(ValueError):
            ManaSpace.from_colors(1, "WUB", families={}, format="standard",
                                  fixed={ManaSource("WUB", "tri"): 1})

    def test_tapped_rates_and_one_mana_per_land(self):
        self.assertEqual([land_availability("tri", t) for t in range(1, 5)],
                         [F(0), F(1, 2), F(2, 3), F(3, 4)])
        base = {ManaSource("UBG", "tri"): 1}
        for cost in ("U", "B", "G"):
            result = evaluate(base, [SpellCost(cost, 1)], model=MODEL, turns=2, opening_hand_size=99)
            self.assertEqual(result.opportunities[0].expected_copies, 0)
            self.assertEqual(result.opportunities[-1].expected_copies, F(1, 2))
        result = evaluate(base, [SpellCost("UB", 1)], model=MODEL, turns=3, opening_hand_size=99)
        self.assertTrue(all(r.expected_copies == 0 for r in result.opportunities))

    def test_no_verge_enabling_types(self):
        base = {ManaSource("UBG", "tri"): 1, ManaSource("UB", "verge"): 1}
        result = evaluate(base, [SpellCost("BB", 1)], model=MODEL, turns=2, opening_hand_size=99)
        self.assertEqual(result.opportunities[-1].expected_copies, 0)

    def test_physical_draw_oracle_and_backend_parity(self):
        base = {ManaSource("UBG", "tri"): 1, ManaSource("UB", "verge"): 1,
                ManaSource("UG", "shock", "UG"): 1}
        spells = [SpellCost("BG", 1), SpellCost("UU", 1), SpellCost("G", 1)]
        result = evaluate(base, spells, model=MODEL, turns=3, opening_hand_size=2)
        for row in result.opportunities:
            seen = min(6, 2+row.turn-(row.position == "play"))
            self.assertEqual(row.expected_copies,
                             physical_oracle(base, spells, seen, row.turn).get(row.cost, 0))
        space = ManaSpace({s: (0, 2) for s in base}, 3)
        args = dict(turns=3, opening_hand_size=2)
        scalar = build_component_table(space, spells, model=MODEL, backend="scalar", **args)
        batch = build_component_table(space, spells, model=MODEL, backend="batch", **args)
        self.assertEqual(scalar, batch)
        self.assertEqual(scalar.rank(), batch.rank())

    def test_deck_constraints_and_budgeted_cached_search(self):
        space = make_space()
        self.assertEqual(sum(MANA_BASE.values()), 26)
        self.assertEqual(spell_components(SPELLS)[0], 34)
        self.assertEqual(space.bounds[ManaSource("UBG", "tri")], (0, 2))
        for base in starting_bases():
            space.counts(base)
            for source, count in FIXED_LANDS.items():
                self.assertEqual(base[source], count)
        evaluator = LocalManaEvaluator(space, SPELLS, model=MODEL, turns=2)
        with patch.object(ManaSpace, "exhaustive", side_effect=AssertionError("global grid")):
            runs, best = optimize(evaluator, budgets=(1, 1, 1))
        self.assertEqual([r.evaluations for r in runs], [1, 1, 1])
        self.assertTrue(all(r.stopped == "evaluation budget" for r in runs))
        self.assertEqual(len(evaluator.cache), 3)
        self.assertGreaterEqual(best.score, runs[0].baseline.score)
        for counts in evaluator.cache:
            self.assertEqual(sum(counts), 26)
            self.assertLessEqual(counts[space.sources.index(ManaSource("UBG", "tri"))], 2)
            for source, count in FIXED_LANDS.items():
                self.assertEqual(counts[space.sources.index(source)], count)
        with patch("mana_search.evaluate", side_effect=AssertionError("cache miss")):
            again, best_again = optimize(evaluator, budgets=(1, 1, 1))
        self.assertEqual(best, best_again)
        self.assertEqual([r.best for r in runs], [r.best for r in again])
