import unittest
from fractions import Fraction
from itertools import product
from examples.moonshadow_fixed_landscape import neighbors
from mana_lands import ManaSource as S
from mana_search import ManaSpace

class LandscapeTests(unittest.TestCase):
    def test_radius_two_matches_complete_small_space(self):
        space=ManaSpace({S('UB','shock','UB'):(0,2),S('BG','shock','BG'):(0,2),
                         S('B','basic'):(0,2),S('G','basic'):(0,2),S('WUBRG','cavern'):(1,1)},5)
        for c in space.exhaustive():
            shocks=sum(n for s,n in zip(space.sources,c) if s.kind=='shock')
            if sum(n for s,n in zip(space.sources,c) if s.kind=='basic')>2:continue
            for radius in (1,2):
                expected={v for v in space.exhaustive() if v!=c and sum(abs(a-b) for a,b in zip(c,v))<=2*radius
                          and sum(n for s,n in zip(space.sources,v) if s.kind=='shock')==shocks
                          and sum(n for s,n in zip(space.sources,v) if s.kind=='basic')<=2}
                self.assertEqual(set(neighbors(space,c,shocks,radius=radius)),expected)


if __name__=='__main__':unittest.main()
