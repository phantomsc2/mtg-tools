import unittest
from collections import Counter
from itertools import product
from math import comb
from unittest.mock import patch
import numpy as np
from mana_batch import binomial_transform
from mana_lands import ManaSource
from mana_model import heuristic_mana_model
from mana_opportunities import CastingMode, Spell, SpellCost, evaluate
from mana_search import ManaSpace, build_component_table
MODEL = heuristic_mana_model()

class BatchTests(unittest.TestCase):

    def test_auto_batches_without_candidate_or_grid_size_cutoffs(self):
        space = ManaSpace({ManaSource(c, 'basic'): (0, 15) for c in 'WUBRG'}, 0)
        spells = [SpellCost('2', 1)]
        expected = build_component_table(space, spells, model=MODEL, backend='scalar', turns=1)
        with patch('mana_search.evaluate', side_effect=AssertionError('Unexpected scalar fallback')):
            self.assertEqual(build_component_table(space, spells, model=MODEL, backend='auto', turns=1), expected)
            self.assertEqual(build_component_table(space, spells, model=MODEL, backend='batch', turns=1), expected)

    def test_town_cavern_and_shock_scores(self):
        shock = ManaSource('UB', 'shock', 'UB')
        town, cavern = (ManaSource('WUBRG', 'town'), ManaSource('WUBRG', 'cavern'))
        space = ManaSpace({shock: (0, 2), town: (0, 2), cavern: (0, 2)}, 3)
        spells = [SpellCost('UU', 2), SpellCost('WB', 1)]
        scalar = build_component_table(space, spells, model=MODEL, backend='scalar')
        batch = build_component_table(space, spells, model=MODEL, backend='batch')
        self.assertEqual(scalar, batch)
        for _ in range(1):
            ranked = batch.rank()
            for row in ranked:
                result = evaluate(dict(zip(space.sources, row.counts)), spells, model=MODEL)
                self.assertAlmostEqual(float(row.score), result.score)
            for parameter in batch.costs:
                self.assertEqual(batch.crossings(parameter), scalar.crossings(parameter))

    def test_transform_against_direct_sums(self):
        values = np.arange(12, dtype=np.int64).reshape(3, 4)
        result = binomial_transform(values)
        for a, b in product(range(3), range(4)):
            expected = sum((comb(a, i) * comb(b, j) * int(values[i, j]) for i in range(a + 1) for j in range(b + 1)))
            self.assertEqual(result[a, b], expected)

    def test_batch_equals_scalar_for_every_component(self):
        space = ManaSpace({ManaSource('U', 'basic'): (0, 2), ManaSource('UG', 'shock', 'UG'): (0, 2), ManaSource('UB', 'verge'): (0, 2), ManaSource('WUBRG', 'town'): (0, 1)}, 3)
        spells = [SpellCost('0', 1), SpellCost('2', 1), SpellCost('U', 2, 0), Spell(2, (CastingMode('BB', 3), CastingMode('UU')), weight=2), SpellCost('1G', 1), SpellCost('9U', 1), SpellCost('UB', 0)]
        for position in ('both', 'play', 'draw'):
            for opening in (0, 2, 20):
                args = dict(position=position, opening_hand_size=opening, turns=3)
                scalar = build_component_table(space, spells, model=MODEL, backend='scalar', **args)
                batch = build_component_table(space, spells, model=MODEL, backend='batch', **args)
                self.assertEqual(scalar, batch, (position, opening))
                self.assertEqual(scalar.rank(), batch.rank())
                self.assertEqual(scalar.crossings('UU'), batch.crossings('UU'))

    def test_fixed_types_and_mixed_typed_untyped_shocks(self):
        space = ManaSpace({ManaSource('B', 'basic'): (1, 1), ManaSource('UG', 'shock', 'UG'): (0, 2), ManaSource('UG', 'shock'): (0, 2), ManaSource('UG', 'verge'): (0, 2)}, 4)
        spells = [SpellCost('GG', 3), SpellCost('UU', 2), SpellCost('1B', 1)]
        self.assertEqual(build_component_table(space, spells, model=MODEL, backend='scalar'), build_component_table(space, spells, model=MODEL, backend='batch'))

    def test_integer_limbs_and_progress_without_scalar_evaluations(self):
        space = ManaSpace({ManaSource('B', 'basic'): (1, 1), ManaSource('UB', 'shock'): (0, 4), ManaSource('WUBRG', 'town'): (0, 26)}, 26)
        spells = [SpellCost('UU', 34)]
        expected = build_component_table(space, spells, model=MODEL, backend='scalar')
        completed, rows = ([], [])

        def progress(costs):
            for cost in costs:
                yield cost
                completed.append(cost)

        def row_progress(candidates):
            for candidate in candidates:
                rows.append(candidate)
                yield candidate
        with patch('mana_search.evaluate', side_effect=AssertionError('Per-base evaluation')):
            with patch('mana_batch.binomial_transform', wraps=binomial_transform) as transform:
                result = build_component_table(space, spells, model=MODEL, backend='batch', component_progress=progress, progress=row_progress)
                self.assertGreater(transform.call_count, 1)
        self.assertEqual(result, expected)
        self.assertEqual(completed, ['UU'])
        self.assertEqual(rows, [r.counts for r in result.rows])

    def test_zero_land_zero_seen_and_empty_spell_cases(self):
        for space, spells, args in ((ManaSpace({}, 0), [SpellCost('0', 2)], {}), (ManaSpace({}, 0), [SpellCost('0', 2)], dict(opening_hand_size=0, turns=1, position='play')), (ManaSpace({ManaSource('U', 'basic'): (1, 1)}, 1), [], {})):
            self.assertEqual(build_component_table(space, spells, model=MODEL, backend='scalar', **args), build_component_table(space, spells, model=MODEL, backend='batch', **args))

    def test_large_integer_mass_falls_back_in_auto(self):
        space = ManaSpace({ManaSource('U', 'basic'): (0, 67), ManaSource('G', 'basic'): (0, 67)}, 67)
        spells = [SpellCost('U', 1)]
        args = dict(opening_hand_size=68, turns=1)
        with self.assertRaises(OverflowError):
            build_component_table(space, spells, model=MODEL, backend='batch', **args)
        self.assertEqual(build_component_table(space, spells, model=MODEL, backend='auto', **args), build_component_table(space, spells, model=MODEL, backend='scalar', **args))

    def test_reference_pool_and_sampled_scalar_agreement(self):
        from examples.sultai import MANA_BASE, SPELLS
        reference = {ManaSource('B', 'basic'): 1, ManaSource('WUBRG', 'cavern'): 4, ManaSource('WUBRG', 'town'): 4}
        reference.update({ManaSource(pair, kind, pair if kind == 'shock' else ''): 4 for kind in ('shock', 'verge') for pair in ('UB', 'UG', 'BG')})
        space = ManaSpace({s: (n, n) if s.kind == 'basic' else (0, 4) for s, n in reference.items()}, 26)
        self.assertEqual(space.candidate_count(), 3144)
        with patch('mana_search.evaluate', side_effect=AssertionError('Auto should batch')):
            table = build_component_table(space, SPELLS, model=MODEL)
        for row in table.rows[::173]:
            result = evaluate(dict(zip(space.sources, row.counts)), SPELLS, model=MODEL)
            totals = Counter()
            for opportunity in result.opportunities:
                totals[opportunity.cost] += opportunity.expected_copies
            self.assertEqual(row.opportunities, tuple((totals[cost] / 14 for cost in table.costs)))
if __name__ == '__main__':
    unittest.main()
