import unittest
from fractions import Fraction
from unittest.mock import patch

from mana_lands import ManaSource
from mana_model import heuristic_mana_model
from mana_opportunities import SpellCost, evaluate
from mana_search import LocalManaEvaluator, ManaSpace, RankedBase, local_search

MODEL = heuristic_mana_model()

U = ManaSource("U", "basic")
B = ManaSource("B", "basic")
D = ManaSource("UB", "shock", types="UB")


class LocalSearchTests(unittest.TestCase):
    def test_family_maximum_limits_total_basics(self):
        space = ManaSpace({U: (0, 3), B: (0, 3), D: (0, 3)}, 4)
        evaluator = LocalManaEvaluator(space, [SpellCost('U', 2)], model=MODEL, turns=2,
                                       opening_hand_size=1, family_maximums={'basic': 2})
        result = local_search(evaluator, {B: 1, D: 3}, shock_penalty=0.01)
        self.assertEqual(result.stopped, 'two-land local optimum')
        self.assertTrue(all(sum(n for source, n in zip(space.sources, counts)
                                if source.kind == 'basic') <= 2 for counts in evaluator.cache))
        self.assertEqual(result.best.counts, space.counts({U: 2, D: 2}))
        with self.assertRaises(ValueError):
            evaluator.value({U: 2, B: 1, D: 1})
        for caps in ({'basic': -1}, {'basic': True}, {'missing': 2}, {'basic': 0}):
            with self.subTest(caps=caps), self.assertRaises(ValueError):
                LocalManaEvaluator(space, [], model=MODEL, family_maximums=caps)
        with self.assertRaises(ValueError):
            LocalManaEvaluator(space, [], model=MODEL, family_totals={'basic': 3}, family_maximums={'basic': 2})

    def test_fixed_family_totals(self):
        space = ManaSpace({U: (0, 3), B: (0, 3), D: (0, 3)}, 4)
        evaluator = LocalManaEvaluator(space, [SpellCost('U', 4)], model=MODEL,
                                       family_totals={'shock': 2}, turns=2, opening_hand_size=1)
        initial = {B: 2, D: 2}
        result = local_search(evaluator, initial)
        self.assertEqual(result.stopped, 'two-land local optimum')
        self.assertTrue(all(counts[space.sources.index(D)] == 2 for counts in evaluator.cache))
        self.assertEqual(result.best.counts, space.counts({U: 2, D: 2}))
        with self.assertRaisesRegex(ValueError, 'family totals'):
            evaluator.value({U: 3, D: 1})
        for totals in ({'shock': True}, {'shock': 4}, {'unknown': 0}, {'basic': 4, 'shock': 2}):
            with self.subTest(totals=totals), self.assertRaises(ValueError):
                LocalManaEvaluator(space, [], model=MODEL, family_totals=totals)

    def test_structured_scores_cache_and_penalties(self):
        space = ManaSpace({U: (0, 2), D: (0, 2)}, 2)
        base = {U: 1, D: 1}
        spells = [SpellCost("U", 2, 0.7), SpellCost("UU", 1, 2)]
        evaluator = LocalManaEvaluator(space, spells, model=MODEL, turns=3, opening_hand_size=2)
        expected = evaluate(base, spells, model=MODEL, turns=3, opening_hand_size=2, shock_penalty=0.1)
        value = evaluator.value(base, shock_penalty=0.1)
        self.assertAlmostEqual(float(value.score), expected.score)
        self.assertIsInstance(value.score, Fraction)
        self.assertEqual(evaluator.components(base).opportunities, expected.opportunities)
        with patch("mana_search.evaluate", side_effect=AssertionError("cache miss")):
            changed = evaluator.value(base, shock_penalty=0.2)
            self.assertEqual(value.score - changed.score, Fraction(1, 10))
        self.assertEqual({(r.turn, r.position) for r in expected.opportunities},
                         {(t, p) for t in range(1, 4) for p in ("play", "draw")})

    def test_multistep_and_exhaustive_local_certificate_without_grid(self):
        space = ManaSpace({U: (0, 3), B: (0, 3), D: (1, 1)}, 4)
        spells = [SpellCost("U", 4)]
        evaluator = LocalManaEvaluator(space, spells, model=MODEL, turns=1, opening_hand_size=2)
        initial = {B: 3, D: 1}
        with patch.object(ManaSpace, "exhaustive", side_effect=AssertionError("grid")), \
                patch("mana_batch.component_columns", side_effect=AssertionError("batch grid")):
            result = local_search(evaluator, initial)
        self.assertEqual(result.stopped, "two-land local optimum")
        self.assertGreaterEqual(len(result.moves), 2)
        self.assertEqual(result.best.counts, space.counts({U: 3, D: 1}))
        previous = result.baseline.score
        for move in result.moves:
            self.assertGreater(move.score, previous)
            self.assertEqual(move.swap.cards_replaced, 1)
            previous = move.score
        # Independently verify the certificate against every legal tiny base.
        for counts in space.exhaustive():
            score = evaluate(dict(zip(space.sources, counts)), spells, model=MODEL, turns=1, opening_hand_size=2).score
            self.assertLessEqual(score, float(result.best.score) + 1e-14)
        again = local_search(evaluator, initial)
        self.assertEqual(again.moves, result.moves)
        self.assertEqual(again.evaluations, result.evaluations)

    def test_budget_partial_and_cached_rerun(self):
        space = ManaSpace({U: (0, 3), B: (0, 3)}, 3)
        evaluator = LocalManaEvaluator(space, [SpellCost("U", 4)], model=MODEL, turns=1)
        initial = {B: 3}
        for budget in (1, 2):
            result = local_search(evaluator, initial, evaluation_budget=budget)
            self.assertEqual(result.evaluations, budget)
            self.assertEqual(result.stopped, "evaluation budget")
            self.assertGreaterEqual(result.best.score, result.baseline.score)
            if budget == 2:
                self.assertGreater(result.best.score, result.baseline.score)
        with patch("mana_search.evaluate", side_effect=AssertionError("cache miss")):
            self.assertEqual(local_search(evaluator, initial, evaluation_budget=2).evaluations, 2)

    def test_plateau_fixed_and_invalid_inputs(self):
        space = ManaSpace({U: (0, 2), B: (0, 2)}, 2)
        evaluator = LocalManaEvaluator(space, [SpellCost("0", 2)], model=MODEL, turns=1)
        result = local_search(evaluator, {B: 2})
        self.assertEqual(result.moves, ())
        self.assertEqual(result.best.counts, result.baseline.counts)
        fixed = LocalManaEvaluator(ManaSpace({U: (2, 2)}, 2), [SpellCost("U", 1)], model=MODEL)
        self.assertEqual(local_search(fixed, {U: 2}, evaluation_budget=1).stopped, "two-land local optimum")
        for budget in (0, -1, True):
            with self.assertRaises(ValueError):
                local_search(evaluator, {B: 2}, evaluation_budget=budget)
        with self.assertRaises(ValueError):
            local_search(evaluator, {B: 3})
        with self.assertRaises(ValueError):
            local_search(evaluator, {B: 2}, shock_penalty=-1)

    def test_staged_completion_check_and_return_to_single_descent(self):
        space = ManaSpace({U: (0, 6), B: (0, 6)}, 6)
        evaluator = LocalManaEvaluator(space, (), model=MODEL, turns=1)
        scores = (0, 2, 1, 3, 5, 4, 0)

        def value(base, **kwargs):
            counts = space.counts(base)
            raw = Fraction(scores[base.get(U, 0)])
            return RankedBase(counts, raw, Fraction(), raw, None, None)

        with patch.object(evaluator, 'value', side_effect=value), patch.object(
                evaluator, 'value_and_swap_deltas', wraps=evaluator.value_and_swap_deltas) as check:
            result = local_search(evaluator, {B: 6}, evaluation_budget=100)
            self.assertEqual(result.stopped, 'two-land local optimum')
            self.assertEqual([call.kwargs['max_replacements'] for call in check.call_args_list],
                             [1, 1, 2, 1, 1, 2])
            self.assertEqual(result.best.counts, space.counts({U: 4, B: 2}))
            self.assertEqual([m.swap.cards_replaced for m in result.moves], [1, 2, 1])
            self.assertEqual(result.evaluations, 7)
            legacy = local_search(evaluator, {B: 6}, max_replacements=1)
            self.assertEqual(legacy.stopped, 'one-land local optimum')
            self.assertEqual(legacy.best.counts, space.counts({U: 1, B: 5}))
            # A complete one-land neighborhood is insufficient to certify two-land optimality.
            limited = local_search(evaluator, {B: 6}, evaluation_budget=3)
            self.assertEqual(limited.stopped, 'evaluation budget')
            self.assertEqual(limited.evaluations, 3)
            # Retain an improving completion move even if subsequent descent hits the budget.
            partial = local_search(evaluator, {B: 6}, evaluation_budget=4)
            self.assertEqual(partial.stopped, 'evaluation budget')
            self.assertEqual(partial.best.counts, space.counts({U: 3, B: 3}))

    def test_coupled_move_preserves_family_total(self):
        green_shock = ManaSource('BG', 'shock', 'BG')
        space = ManaSpace({D: (0, 1), green_shock: (0, 1), U: (0, 1), B: (0, 1)}, 2)
        evaluator = LocalManaEvaluator(space, (), model=MODEL, turns=1,
                                       family_totals={'shock': 1}, family_maximums={'basic': 1})
        initial, target = {D: 1, U: 1}, {green_shock: 1, B: 1}
        start_counts, target_counts = space.counts(initial), space.counts(target)

        def value(base, **kwargs):
            counts = space.counts(base)
            self.assertTrue(evaluator._eligible(counts))
            raw = Fraction(3 if counts == target_counts else 2 if counts == start_counts else 0)
            return RankedBase(counts, raw, Fraction(), raw, None, None)

        self.assertNotIn(target_counts, evaluator.neighbor_counts(initial))
        self.assertIn(target_counts, evaluator.neighbor_counts(initial, max_replacements=2))
        with patch.object(evaluator, 'value', side_effect=value):
            result = local_search(evaluator, initial)
        self.assertEqual(result.best.counts, target_counts)
        self.assertEqual(result.stopped, 'two-land local optimum')
        self.assertEqual(result.moves[0].swap.cards_replaced, 2)

    def test_completion_budget_and_warm_cache(self):
        space = ManaSpace({U: (0, 2), B: (0, 2)}, 2)
        evaluator = LocalManaEvaluator(space, [SpellCost('0', 2)], model=MODEL, turns=1)
        initial = {B: 2}
        limited = local_search(evaluator, initial, evaluation_budget=2)
        self.assertEqual(limited.stopped, 'evaluation budget')
        complete = local_search(evaluator, initial, evaluation_budget=3)
        self.assertEqual(complete.stopped, 'two-land local optimum')
        with patch('mana_search.evaluate', side_effect=AssertionError('cache miss')):
            repeated = local_search(evaluator, initial, evaluation_budget=2)
        # Warm caches do not waive visit limits.
        self.assertEqual(repeated.evaluations, limited.evaluations)
        self.assertEqual(repeated.stopped, 'evaluation budget')
        for radius in (0, 3, True, 1.5):
            with self.subTest(radius=radius):
                with self.assertRaises(ValueError):
                    evaluator.neighbor_counts(initial, max_replacements=radius)
                with self.assertRaises(ValueError):
                    local_search(evaluator, initial, max_replacements=radius)

    def test_exact_swap_deltas(self):
        space = ManaSpace({U: (0, 2), B: (0, 2), D: (1, 1)}, 3)
        evaluator = LocalManaEvaluator(space, [SpellCost("U", 3)], model=MODEL, turns=2)
        base = {B: 1, U: 1, D: 1}
        neighborhood = evaluator.value_and_swap_deltas(base, shock_penalty=0.1)
        self.assertTrue(neighborhood.complete)
        self.assertEqual(len(neighborhood.neighbors), 2)
        for neighbor in neighborhood.neighbors:
            self.assertEqual(neighbor.delta, neighbor.score - neighborhood.current.score)
            self.assertEqual(neighbor.swap.cards_replaced, 1)
            candidate = dict(zip(space.sources, neighbor.counts))
            self.assertEqual(candidate[D], 1)
            self.assertEqual(sum(candidate.values()), 3)
            self.assertAlmostEqual(float(neighbor.score),
                                   evaluate(candidate, [SpellCost("U", 3)], model=MODEL, turns=2,
                                            shock_penalty=0.1).score)


if __name__ == "__main__":
    unittest.main()
