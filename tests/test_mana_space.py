import pickle
import unittest
from fractions import Fraction
from itertools import product

from mtg_tools.mana.lands import ManaSource as S
from mtg_tools.mana.policy import heuristic_mana_model
from mtg_tools.mana.evaluation import OpportunityResult, evaluate
from mtg_tools.mana.spells import SpellCost
from mtg_tools.mana.tables import BaseComponents, ComponentTable, build_component_table
from mtg_tools.mana.evaluation import LocalManaEvaluator
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.local import local_search


class FamilySpaceTests(unittest.TestCase):
    def setUp(self):
        self.u,self.b,self.ub,self.bg,self.town,self.cavern=(S('U','basic'),S('B','basic'),
            S('UB','shock','UB'),S('BG','shock','BG'),S('WUBRG','town'),S('WUBRG','cavern'))
        self.bounds={s:(0,2) for s in (self.u,self.b,self.ub,self.bg)}
        self.bounds.update({self.town:(0,1),self.cavern:(1,1)})

    def test_ranges_count_enumeration_and_neighbors_against_cartesian_oracle(self):
        for limits in ({'shock':(1,3),'basic':(0,2),'town':(0,1)},
                       {'shock':(2,2),'town':(1,1)}, {'shock':(0,4),'basic':(1,2)}):
            space=ManaSpace(self.bounds,5,limits)
            expected=set()
            for c in product(*(range(lo,hi+1) for lo,hi in space.bounds.values())):
                if sum(c)!=5:continue
                valid=all(lo<=sum(n for s,n in zip(space.sources,c) if s.kind==kind)<=hi
                          for kind,(lo,hi) in limits.items())
                if valid:
                    expected.add(c)
                    self.assertEqual(space.counts(dict(zip(space.sources,c))),c)
                else:
                    with self.assertRaises(ValueError):space.counts(dict(zip(space.sources,c)))
            self.assertEqual(set(space.exhaustive()),expected)
            self.assertEqual(space.candidate_count(),len(expected))
            ev=LocalManaEvaluator(space,(),model=heuristic_mana_model(),turns=1)
            for c in expected:
                found=set(ev.neighbor_counts(dict(zip(space.sources,c)),max_replacements=2))
                self.assertEqual(found,{v for v in expected if v!=c and sum(abs(a-b) for a,b in zip(c,v))<=4})

    def test_infeasible_and_invalid_ranges(self):
        for limits in ({'shock':(3,2)},{'shock':(-1,2)},{'shock':(True,2)},
                       {'shock':(0,1.5)},{'shock':None},{'fast':(0,0)},
                       {'shock':(5,6)},{'shock':(3,4),'basic':(2,4),'town':(1,1)}):
            with self.subTest(limits=limits),self.assertRaises(ValueError):
                ManaSpace(self.bounds,5,limits)
        space=ManaSpace(self.bounds,5,{'shock':(0,100)})
        self.assertGreater(space.candidate_count(),0)
        self.assertEqual(ManaSpace({},0).candidate_count(),1)
        self.assertEqual(list(ManaSpace({},0).exhaustive()),[()])
        source_space=ManaSpace.from_colors(2,'UB',families={'basic':(0,2),'shock':(0,2)},family_bounds={'shock':(1,1)})
        self.assertTrue(all(sum(n for s,n in zip(source_space.sources,c) if s.kind=='shock')==1
                            for c in source_space.exhaustive()))
        with self.assertRaises(TypeError):source_space.family_bounds['shock']=(0,2)
        original={'shock':[1,2]}
        copied=ManaSpace(self.bounds,5,original)
        original['shock'][1]=0
        self.assertEqual(copied.family_bounds['shock'],(1,2))
        with self.assertRaises(ValueError):ManaSpace(self.bounds,5,{'cavern':(0,0)})


    def test_constrained_backend_parity_and_raw_scoring(self):
        space=ManaSpace(self.bounds,5,{'shock':(1,2),'basic':(1,2),'town':(0,1)})
        spells=[SpellCost('UB',2,1.5),SpellCost('1G',1)]
        args=dict(model=heuristic_mana_model(),half_life=.5,opening_hand_size=3)
        scalar=build_component_table(space,spells,backend='scalar',**args)
        batch=build_component_table(space,spells,backend='batch',**args)
        self.assertEqual(scalar.rows,batch.rows)
        self.assertEqual(len(batch.rows),space.candidate_count())
        ev=LocalManaEvaluator(space,spells,**args)
        for row in batch.rank():
            base=dict(zip(space.sources,row.counts))
            self.assertEqual(ev.value(base).score,row.score)
            self.assertAlmostEqual(float(row.score),evaluate(base,spells,**args).score)
            self.assertFalse(hasattr(row,'raw_score'))
            self.assertFalse(hasattr(row,'penalty'))
        initial=dict(zip(space.sources,next(space.exhaustive())))
        result=local_search(ev,initial,evaluation_budget=2000)
        self.assertEqual(result.stopped,'two-land local optimum')
        for c in ev.neighbor_counts(dict(zip(space.sources,result.best.counts)),max_replacements=2):
            self.assertLessEqual(ev.value(dict(zip(space.sources,c))).score,result.best.score)

    def test_new_cache_schema_and_rejected_legacy_results(self):
        space=ManaSpace({self.u:(1,1)},1)
        ev=LocalManaEvaluator(space,[SpellCost('U',1)],model=heuristic_mana_model(),turns=1)
        ev.value({self.u:1})
        self.assertEqual(ev.cache_signature[0],'raw-score-v2')
        with self.assertRaises(ValueError):ev.restore_cache(ev.cache_signature[1:],dict(ev.cache))
        result=evaluate({self.u:1},[SpellCost('U',1)],model=heuristic_mana_model())
        self.assertEqual(pickle.loads(pickle.dumps(result)),result)
        legacy=object.__new__(OpportunityResult)
        for name,value in {'opportunities':(),'raw_score':1.,'penalty':.1,'score':.9}.items():
            object.__setattr__(legacy,name,value)
        with self.assertRaisesRegex(ValueError,'rebuild'):pickle.loads(pickle.dumps(legacy))
        table=build_component_table(space,[SpellCost('U',1)],model=heuristic_mana_model())
        # ManaSpace mappings are intentionally immutable; cached table rows are persisted separately.
        old_row=object.__new__(BaseComponents)
        for name,value in {'counts':(1,),'opportunities':(Fraction(1),),'shock_count':0,'town_count':0}.items():
            object.__setattr__(old_row,name,value)
        with self.assertRaisesRegex(ValueError,'rebuild'):pickle.loads(pickle.dumps(old_row))
        with self.assertRaises(ValueError):table.__setstate__({'space':space})
        table.rank()
        restored=object.__new__(ComponentTable)
        restored.__setstate__(vars(table).copy())
        self.assertEqual(restored,table)

        for fn in (evaluate,):
            with self.assertRaises(TypeError):fn({self.u:1},[],model=heuristic_mana_model(),shock_penalty=0)
        with self.assertRaises(TypeError):LocalManaEvaluator(space,[],model=heuristic_mana_model(),family_totals={'basic':1})

if __name__=='__main__':unittest.main()
