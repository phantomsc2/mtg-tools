import unittest
from fractions import Fraction as F
from itertools import product
from unittest.mock import patch

from mana_opportunities import ManaSource, SpellCost, evaluate
from mana_search import BaseComponents, ComponentTable, Interval, ManaSpace, build_component_table

U = ManaSource("U", "basic")
B = ManaSource("B", "basic")
D = ManaSource("UB", "dual")
R = ManaSource("WUBRG", "rainbow")


class ManaSearchTests(unittest.TestCase):
    def test_candidates_against_cartesian_enumeration(self):
        space = ManaSpace({U: (1, 3), B: (0, 2), D: (0, 1)}, 3)
        expected = {counts for counts in product(*(range(lo, hi + 1) for lo, hi in space.bounds.values()))
                    if sum(counts) == 3}
        self.assertEqual(set(space.exhaustive()), expected)
        self.assertEqual(space.candidate_count(), len(expected))
        baseline = {U: 2, B: 1}
        reference = space.counts(baseline)
        local = tuple(space.one_swap(baseline))
        expected_local = {counts for counts in expected if sum(abs(a - b) for a, b in zip(counts, reference)) <= 2}
        self.assertEqual(set(local), expected_local)
        self.assertEqual(len(local), len(set(local)))
        self.assertEqual(local[0], reference)

    def test_components_and_rank_agree_with_evaluator(self):
        space = ManaSpace({U: (0, 2), D: (0, 2), R: (0, 1)}, 2)
        spells = [SpellCost("U", 2, 0.5), SpellCost("U", 1, 2), SpellCost("BU", 1, 3)]
        table = build_component_table(space, spells, turns=3, opening_hand_size=2)
        for row in table.rank(dual_penalty=F(1, 10), rainbow_penalty=F(1, 5)):
            base = dict(zip(space.sources, row.counts))
            expected = evaluate(base, spells, turns=3, opening_hand_size=2,
                                dual_penalty=0.1, rainbow_penalty=0.2)
            self.assertAlmostEqual(float(row.raw_score), expected.raw_score)
            self.assertAlmostEqual(float(row.score), expected.score)
        self.assertEqual(table.default_weights[table.costs.index("U")], 1)
        for row in table.rank({"UB": 0, "U": 2}):
            expected = evaluate(dict(zip(space.sources, row.counts)),
                                [SpellCost("U", 3, 2), SpellCost("UB", 1, 0)],
                                turns=3, opening_hand_size=2)
            self.assertAlmostEqual(float(row.score), expected.score)
        self.assertTrue(all(isinstance(value, F) for row in table.rows for value in row.opportunities))
        with patch("mana_search.evaluate", side_effect=AssertionError("Unexpected draw calculation")):
            table.rank({"U": 3})
            table.crossings("U")

    def test_one_swap_scores_and_scope(self):
        space = ManaSpace({U: (0, 3), B: (0, 3), D: (0, 2)}, 3)
        base = {U: 2, B: 1}
        spells = [SpellCost("UU", 2), SpellCost("BB", 1)]
        full = build_component_table(space, spells, baseline=base, opening_hand_size=2, turns=2)
        local = build_component_table(space, spells, mode="one_swap", baseline=base,
                                      opening_hand_size=2, turns=2)
        full_rows = {row.counts: row for row in full.rows}
        for row in local.rows:
            self.assertEqual(row, full_rows[row.counts])
        for row in local.rank():
            self.assertIn(row.swap.cards_replaced, (0, 1))
            self.assertEqual(sum(n for _, n in row.swap.incoming), row.swap.cards_replaced)
        self.assertEqual(local.crossings("UU").mode, "one_swap")
        self.assertEqual(local.crossings("UU").baseline, space.counts(base))
        self.assertGreaterEqual(full.rank()[0].score, local.rank()[0].score)

    def line_table(self):
        space = ManaSpace({U: (0, 3), B: (0, 3)}, 3)
        # Score lines: 9/2, 4+x, 2+2x, 3x. Baseline wins at x=1.
        lines = [(F(9, 2), 0), (4, 1), (2, 2), (0, 3)]
        counts = tuple(space.exhaustive())
        rows = tuple(BaseComponents(base, (F(b), F(a)), 0, 0) for base, (a, b) in zip(counts, lines))
        return ComponentTable(space, ("U", "B"), (F(1), F(1)), rows, "exhaustive", counts[1])

    def test_exact_bidirectional_crossings_and_simultaneous_tie(self):
        table = self.line_table()
        result = table.crossings("U")
        self.assertTrue(result.baseline_is_optimal)
        self.assertEqual(result.optimal_interval, Interval(F(1, 2), F(2)))
        self.assertEqual(result.lower.value, F(1, 2))
        self.assertEqual(result.lower.counts, table.rows[0].counts)
        self.assertEqual(result.upper.value, 2)
        self.assertEqual(result.upper.counts, table.rows[3].counts)
        self.assertEqual(result.upper.optimal_interval, Interval(F(2), None))
        for transition, side in ((result.lower, -1), (result.upper, 1)):
            at = {row.counts: row.score for row in table.rank({"U": transition.value})}
            self.assertEqual(at[result.baseline], at[transition.counts])
            beyond = table.rank({"U": transition.value + side * F(1, 100)})[0]
            self.assertEqual(beyond.counts, transition.counts)
        self.assertEqual(result.comparisons[0].better, "below")
        self.assertEqual(result.comparisons[0].tie_at, F(1, 2))

    def test_nonoptimal_reference_gets_pairwise_comparisons(self):
        table = self.line_table()
        reference = table.rows[2].counts
        result = table.crossings("U", baseline=dict(zip(table.space.sources, reference)))
        self.assertFalse(result.baseline_is_optimal)
        self.assertEqual(result.optimal_interval, Interval(F(2), F(2)))
        self.assertIsNone(result.lower)
        self.assertIsNone(result.upper)
        self.assertEqual(len(result.comparisons), 3)

    def test_penalty_crossings(self):
        for source, parameter in ((D, "dual_penalty"), (R, "rainbow_penalty")):
            space = ManaSpace({U: (0, 1), source: (0, 1)}, 1)
            rows = tuple(BaseComponents(c, (F(2 if c[space.sources.index(source)] else 1),),
                                       c[space.sources.index(source)] if source == D else 0,
                                       c[space.sources.index(source)] if source == R else 0)
                         for c in space.exhaustive())
            table = ComponentTable(space, ("U",), (F(1),), rows, "exhaustive", None)
            result = table.crossings(parameter)
            self.assertTrue(result.baseline_is_optimal)
            self.assertEqual(result.upper.value, 1)
            self.assertEqual(result.optimal_interval, Interval(F(0), F(1)))

    def test_parallel_lines_zero_boundary_and_no_crossing(self):
        table = self.line_table()
        counts = tuple(row.counts for row in table.rows)
        rows = tuple(BaseComponents(c, (F(slope), F(intercept)), 0, 0)
                     for c, intercept, slope in zip(counts, (1, 1, 0, 2), (1, 1, 1, 0)))
        table = ComponentTable(table.space, ("U", "B"), (F(0), F(1)), rows, "exhaustive", counts[0])
        result = table.crossings("U")
        self.assertFalse(result.baseline_is_optimal)
        self.assertEqual(result.comparisons[0].better, "tied")
        self.assertEqual(result.comparisons[1].better, "never")
        self.assertEqual(result.optimal_interval, Interval(F(1), None))
        at_boundary = table.crossings("U", weights={"U": 1})
        self.assertTrue(at_boundary.baseline_is_optimal)
        self.assertEqual(at_boundary.lower.value, 1)
        self.assertIsNone(at_boundary.upper)
        zero = table.crossings("U", weights={"U": 0, "B": 0})
        self.assertTrue(zero.baseline_is_optimal)
        self.assertEqual(zero.optimal_interval, Interval(F(0), None))
        self.assertIsNone(zero.lower)
        self.assertIsNone(zero.upper)

    def test_empty_spells_and_fixed_pool(self):
        space = ManaSpace({U: (1, 1)}, 1)
        table = build_component_table(space, [])
        self.assertEqual(table.rank()[0].score, 0)
        self.assertEqual(space.candidate_count(), 1)
        self.assertIsNone(table.crossings("dual_penalty").upper)
        space = ManaSpace({}, 0)
        self.assertEqual(space.candidate_count(), 1)
        table = build_component_table(space, [SpellCost("0", 2)])
        self.assertEqual(table.rank()[0].score, 2)

    def test_transition_at_zero_and_dominated_parallel_reference(self):
        space = ManaSpace({U: (0, 2), B: (0, 2)}, 2)
        counts = tuple(space.exhaustive())
        rows = tuple(BaseComponents(c, (F(slope), F(intercept)), 0, 0)
                     for c, intercept, slope in zip(counts, (1, 1, 0), (0, 1, 0)))
        table = ComponentTable(space, ("U", "B"), (F(0), F(1)), rows, "exhaustive", counts[0])
        result = table.crossings("U")
        self.assertTrue(result.baseline_is_optimal)
        self.assertEqual(result.optimal_interval, Interval(F(0), F(0)))
        self.assertEqual(result.upper.value, 0)
        self.assertEqual(result.upper.counts, counts[1])
        self.assertIsNone(result.lower)
        dominated = table.crossings("U", baseline=dict(zip(space.sources, counts[2])))
        self.assertFalse(dominated.baseline_is_optimal)
        self.assertIsNone(dominated.optimal_interval)

    def test_invalid_inputs(self):
        for bounds, total in (({U: (-1, 2)}, 1), ({U: (2, 1)}, 1), ({U: (0, 1)}, 2),
                              ({U: (0, True)}, 1), ({U: (0, 2)}, -1)):
            with self.assertRaises(ValueError):
                ManaSpace(bounds, total)
        space = ManaSpace({U: (0, 2), B: (0, 2)}, 2)
        for base in ({U: 1}, {D: 2}, {U: -1, B: 3}):
            with self.assertRaises(ValueError):
                space.counts(base)
        with self.assertRaises(ValueError):
            build_component_table(space, [SpellCost("U", 1)], mode="one_swap")
        table = build_component_table(space, [SpellCost("U", 1)])
        for weights in ({"B": 1}, {"U": -1}, {"U": float("nan")}):
            with self.assertRaises(ValueError):
                table.rank(weights)
        with self.assertRaises(ValueError):
            table.crossings("B")


if __name__ == "__main__":
    unittest.main()
