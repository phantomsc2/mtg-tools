import unittest
from fractions import Fraction
from math import inf, nan

from mana_lands import ManaSource
from mana_model import heuristic_mana_model
from mana_opportunities import CastingMode, Spell, SpellCost, evaluate
from mana_search import LocalManaEvaluator, ManaSpace, build_component_table
from mana_timing import resolve_timing


class TurnTimingTests(unittest.TestCase):
    def test_horizons_and_minimality(self):
        for h, horizon in ((2, 9), (3, 13), (1, 5), (0.01, 1)):
            timing = resolve_timing(half_life=h)
            self.assertEqual(timing.horizon, horizon)
            self.assertLess(timing.omitted_mass, .05)
            self.assertGreaterEqual(2**(-(horizon - 1)/h), .05)
            self.assertEqual(sum(timing.weights), 1)
        # Strict inequality excludes the exact 1/8 boundary.
        self.assertEqual(resolve_timing(half_life=1, tail_tolerance=.125).horizon, 4)
        self.assertEqual(resolve_timing().weights, (Fraction(1, 7),)*7)

    def test_invalid_inputs(self):
        for value in (0, -1, True, inf, nan, '2'):
            with self.subTest(h=value), self.assertRaises(ValueError):
                resolve_timing(half_life=value)
        for value in (0, 1, -1, True, inf, nan):
            with self.subTest(tolerance=value), self.assertRaises(ValueError):
                resolve_timing(tail_tolerance=value)
        with self.assertRaises(ValueError):
            resolve_timing(turns=7, half_life=2)

    def test_scoring_paths_and_cache_identity(self):
        u = ManaSource('U', 'basic')
        dual = ManaSource('UB', 'slow')
        space = ManaSpace({u: (0, 2), dual: (0, 2)}, 2)
        spells = (Spell(2, (CastingMode('U'), CastingMode('1UU'))), SpellCost('B', 1))
        model = heuristic_mana_model()
        timing = resolve_timing(half_life=.5)
        for position in ('play', 'draw', 'both'):
            kwargs = dict(model=model, half_life=.5, position=position, opening_hand_size=1)
            local = LocalManaEvaluator(space, spells, **kwargs)
            scalar = build_component_table(space, spells, backend='scalar', **kwargs)
            batch = build_component_table(space, spells, backend='batch', **kwargs)
            self.assertEqual(scalar.rows, batch.rows)
            self.assertEqual(scalar.timing_signature, timing.signature)
            ranked = {row.counts: row for row in batch.score(shock_penalty=.008).rank()}
            for base in ({u: 2}, {u: 1, dual: 1}, {dual: 2}):
                rows = evaluate(base, spells, **kwargs)
                uniform = evaluate(base, spells, model=model, turns=timing.horizon,
                                   position=position, opening_hand_size=1)
                self.assertEqual(rows.opportunities, uniform.opportunities)
                expected = sum(r.weighted_contribution*float(timing.weights[r.turn-1])
                               for r in uniform.opportunities)/(2 if position == 'both' else 1)
                self.assertAlmostEqual(rows.raw_score, expected)
                score = local.value(base, shock_penalty=.008)
                self.assertEqual(score.raw_score, ranked[space.counts(base)].raw_score)
                self.assertAlmostEqual(float(score.raw_score), rows.raw_score)
                self.assertAlmostEqual(local.components(base).raw_score, rows.raw_score)
            compatible = LocalManaEvaluator(space, spells, **kwargs)
            compatible.restore_cache(local.cache_signature, dict(local.cache))
            different = LocalManaEvaluator(space, spells, **{**kwargs, 'half_life': .6})
            self.assertEqual(different.timing.horizon, local.timing.horizon)
            with self.assertRaises(ValueError):
                different.restore_cache(local.cache_signature, dict(local.cache))

    def test_decay_with_fast_lands_towns_and_verges(self):
        sources = (ManaSource('UB', 'shock', 'UB'), ManaSource('UG', 'fast'),
                   ManaSource('WUBRG', 'town'), ManaSource('BG', 'verge'))
        space = ManaSpace({source: (0, 1) for source in sources}, 3)
        spells = (SpellCost('UBG', 2), SpellCost('1UU', 1))
        model = heuristic_mana_model()
        kwargs = dict(model=model, half_life=1, opening_hand_size=3)
        scalar = build_component_table(space, spells, backend='scalar', **kwargs)
        batch = build_component_table(space, spells, backend='batch', **kwargs)
        self.assertEqual(scalar.rows, batch.rows)
        local = LocalManaEvaluator(space, spells, **kwargs)
        for row in batch.score(shock_penalty=.008, town_penalty=.015).rank():
            base = dict(zip(space.sources, row.counts))
            result = local.value(base, shock_penalty=.008, town_penalty=.015)
            self.assertEqual(result.score, row.score)

    def test_penalties_are_not_discounted(self):
        shock = ManaSource('UB', 'shock', 'UB')
        town = ManaSource('WUBRG', 'town')
        result = evaluate({shock: 2, town: 1}, [SpellCost('U', 2)],
                          model=heuristic_mana_model(), half_life=2,
                          shock_penalty=.008, town_penalty=.015)
        self.assertAlmostEqual(result.raw_score-result.score, .031)


if __name__ == '__main__':
    unittest.main()
