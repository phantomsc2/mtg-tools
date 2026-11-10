import unittest
from mana_lands import ManaSource
from mana_model import heuristic_mana_model
from mana_opportunities import SpellCost, evaluate
from mana_search import ManaSpace, LocalManaEvaluator, build_component_table

class FixedCountComparisonTests(unittest.TestCase):
    def test_score_for_same_base_is_independent_of_space_constraints(self):
        shock=ManaSource('UB','shock','UB')
        basic=ManaSource('U','basic')
        bounds={shock:(0,3),basic:(0,3)}
        spells=[SpellCost('UU',2)]
        broad=ManaSpace(bounds,3,{'shock':(1,3)})
        for total in (1,2,3):
            exact=ManaSpace(bounds,3,{'shock':(total,total)})
            base={shock:total,basic:3-total}
            args=dict(model=heuristic_mana_model(),turns=3)
            a=LocalManaEvaluator(broad,spells,**args).value(base)
            b=LocalManaEvaluator(exact,spells,**args).value(base)
            self.assertEqual(a.score,b.score)
            self.assertAlmostEqual(float(a.score),evaluate(base,spells,**args).score)
            self.assertEqual(build_component_table(exact,spells,**args).rank()[0].score,a.score)

if __name__=='__main__':unittest.main()
