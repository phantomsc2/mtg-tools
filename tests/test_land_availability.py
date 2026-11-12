import unittest
from collections import Counter
from fractions import Fraction as F
from itertools import combinations, product
from math import comb, prod

from mtg_tools.mana_lands import ManaSource, land_availability
from mtg_tools.mana_model import heuristic_mana_model
from mtg_tools.mana_opportunities import SpellCost, evaluate
from mtg_tools.mana_search import ManaSpace, build_component_table

MODEL = heuristic_mana_model()


def oracle_rate(kind, turn):
    if kind in ("tapped", "tri", "typed_tapped") or kind in ("town", "fast") and turn > 3 or kind == "slow" and turn < 3:
        return F(turn-1, turn)
    return F(1)


def physical_oracle(base, spells, seen, turn, availability=None):
    """Enumerate physical draws, color assignments, and independent failures."""
    deck = [s for s, n in base.items() for _ in range(n)]
    deck += [s.cost for s in spells for _ in range(s.count)]
    result = Counter()
    for indices in combinations(range(len(deck)), seen):
        hand = [deck[i] for i in indices]
        lands = [s for s in hand if isinstance(s, ManaSource)]
        from test_verges import can_pay_physical
        rates = [(oracle_rate(s.kind, turn) if availability is None else availability(s, turn)) for s in lands]
        for flags in product((False, True), repeat=len(lands)):
            mass = prod(r if flag else 1-r for r, flag in zip(rates, flags))
            if not mass:
                continue
            available = [s for s, flag in zip(lands, flags) if flag]
            for cost in (s for s in hand if isinstance(s, str)):
                total = int(cost.rstrip("WUBRG") or 0) + sum(c in "WUBRG" for c in cost)
                if len(available) >= total and can_pay_physical(available, cost, turn, seen_types="".join(s.types for s in lands)):
                    result[cost] += mass
    return {cost: F(value, comb(len(deck), seen)) for cost, value in result.items()}


class AvailabilityTests(unittest.TestCase):
    def test_arbitrary_simultaneous_rates(self):
        def schedule(kind, turn):
            return {"basic": F(1), "shock": F(0),
                    "town": F(1, 2) if turn % 2 else F(2, 5),
                    "tapped": F(2, 3) if turn % 2 else F(3, 7)}[kind]

        base = {ManaSource(colors, kind): 2 for colors, kind in
                (("U", "basic"), ("UB", "shock"), ("WUBRG", "town"), ("UB", "tapped"))}
        spells = [SpellCost(cost, 1) for cost in ("0", "U", "2", "2U", "4U")]
        space = ManaSpace({s: (0, n) for s, n in base.items()}, 5)
        availability = lambda source, turn: schedule(source.kind, turn)
        custom = heuristic_mana_model(availability=availability)
        for position, opening in (("play", 0), ("draw", 2), ("both", 99)):
            args = dict(turns=5, position=position, opening_hand_size=opening)
            self.assertEqual(build_component_table(space, spells, model=custom, backend="scalar", **args),
                             build_component_table(space, spells, model=custom, backend="batch", **args))
        # Independent physical-outcome enumeration, including repeated rates.
        small = {s: 1 for s in base}
        sample = [SpellCost("2U", 1)]
        result = evaluate(small, sample, model=custom, turns=3, opening_hand_size=99, position="play")
        expected = physical_oracle(small, sample, 5, 3, availability=availability)
        self.assertEqual(result.opportunities[-1].expected_copies, expected["2U"])
        fixed = ManaSpace({s: (1, 1) for s in small}, 4)
        self.assertEqual(build_component_table(fixed, sample, model=custom, backend="scalar", turns=3),
                         build_component_table(fixed, sample, model=custom, backend="batch", turns=3))

    def test_class_rates_and_pool_generation(self):
        expected = {"fast": [1, 1, 1, F(3,4), F(4,5)],
                    "town": [1, 1, 1, F(3,4), F(4,5)],
                    "slow": [0, F(1,2), 1, 1, 1],
                    "tapped": [0, F(1,2), F(2,3), F(3,4), F(4,5)]}
        for kind, rates in expected.items():
            self.assertEqual([land_availability(kind, t) for t in range(1,6)], rates)
        for kind in ("basic", "shock", "verge", "cavern"):
            self.assertTrue(all(land_availability(kind,t) == 1 for t in range(1,6)))
        for kind in ("fast", "slow", "tapped"):
            space = ManaSpace.from_colors(2, "WUBRG", families={kind: (0,4)})
            self.assertEqual(len(space.sources), 10)
            self.assertTrue(all(not s.types and len(s.colors) == 2 for s in space.sources))
            with self.assertRaises(ValueError):
                ManaSource("UB", kind, "UB")
        for args in (("fetch",1),("town",0),("slow",True)):
            with self.assertRaises(ValueError):
                land_availability(*args)

    def test_analytic_factors(self):
        town, basic = ManaSource("WUBRG","town"), ManaSource("U","basic")
        tapped = ManaSource("UB","tapped")
        cases = [({town:1,basic:3}, "4", 4, F(3,4)),
                 ({town:4}, "4", 4, F(81,256)),
                 ({tapped:2}, "U", 2, F(3,4)),
                 ({tapped:2}, "WW", 2, F(0)),
                 ({tapped:2}, "0", 1, F(1)),
                 ({ManaSource("UB","slow"):2}, "UU", 2, F(1,4))]
        for base, cost, turn, expected in cases:
            with self.subTest(cost=cost, base=base):
                result = evaluate(base,[SpellCost(cost,1)], model=MODEL,turns=turn,opening_hand_size=99,position="play")
                self.assertEqual(result.opportunities[-1].expected_copies,expected)

    def test_enumerated_draws_and_failures(self):
        base = {ManaSource("UB","fast"):1, ManaSource("UB","slow"):1,
                ManaSource("UG","tapped"):1, ManaSource("UG","shock","UG"):1,
                ManaSource("UB","verge"):1, ManaSource("WUBRG","town"):1}
        spells = [SpellCost("BB",1), SpellCost("1G",1), SpellCost("0",1)]
        for opening in (0,2,99):
            result = evaluate(base,spells, model=MODEL,turns=4,opening_hand_size=opening)
            for row in result.opportunities:
                seen = min(9,opening+row.turn-(row.position=="play"))
                expected = physical_oracle(base,spells,seen,row.turn)
                self.assertEqual(row.expected_copies,expected.get(row.cost,0),row)

    def test_batch_matches_scalar_with_every_class(self):
        space = ManaSpace.from_colors(3,"UB",families={k:(0,1) for k in
            ("basic","shock","verge","town","fast","slow","tapped")})
        spells = [SpellCost("BB",1),SpellCost("2U",1),SpellCost("UB",1),SpellCost("0",1)]
        for position, opening in (("play",0),("draw",2),("both",99)):
            args = dict(turns=5,position=position,opening_hand_size=opening)
            scalar = build_component_table(space,spells, model=MODEL,backend="scalar",**args)
            batch = build_component_table(space,spells, model=MODEL,backend="batch",**args)
            self.assertEqual(scalar,batch)
            self.assertEqual(scalar.rank(),batch.rank())
            self.assertEqual(scalar.crossings("BB"),batch.crossings("BB"))

    def test_availability_and_colors_must_come_from_the_same_sources(self):
        cases = [({ManaSource("UB", "tapped"):1, ManaSource("R", "basic"):1}, "U", 1, F(0)),
                 ({ManaSource("UB", "tapped"):1, ManaSource("U", "basic"):1,
                   ManaSource("G", "basic"):1}, "UB", 2, F(1,2)),
                 ({ManaSource("UR", "tapped"):1, ManaSource("BG", "tapped"):1,
                   ManaSource("R", "basic"):1}, "UB", 2, F(1,4))]
        for base, cost, turn, expected in cases:
            with self.subTest(base=base):
                result = evaluate(base, [SpellCost(cost,1)], model=MODEL, turns=turn, opening_hand_size=99)
                self.assertEqual(result.opportunities[-1].expected_copies, expected)
                space = ManaSpace({s:(n,n) for s,n in base.items()}, sum(base.values()))
                args = dict(turns=turn, opening_hand_size=99)
                self.assertEqual(build_component_table(space,[SpellCost(cost,1)], model=MODEL,backend="scalar",**args),
                                 build_component_table(space,[SpellCost(cost,1)], model=MODEL,backend="batch",**args))

    def test_no_cards_seen_with_unreliable_sources(self):
        space = ManaSpace.from_colors(1, "UB", families={"slow":(0,1), "tapped":(0,1)})
        spells = [SpellCost("0",1), SpellCost("U",1)]
        args = dict(turns=1,position="play",opening_hand_size=0)
        scalar = build_component_table(space,spells, model=MODEL,backend="scalar",**args)
        self.assertEqual(scalar,build_component_table(space,spells, model=MODEL,backend="batch",**args))
        self.assertTrue(all(not any(row.opportunities) for row in scalar.rows))
