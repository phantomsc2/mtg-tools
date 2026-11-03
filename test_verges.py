import unittest
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import comb

from mana_lands import ManaSource, VERGE_RULES
from mana_opportunities import CastingMode, Spell, SpellCost, evaluate
from mana_search import ManaSpace, build_component_table


def can_pay_physical(lands, cost, turn):
    """Physical-draw oracle with enabling types from all seen lands."""
    primary = {"WU": "W", "WB": "B", "WR": "W", "WG": "G", "UB": "U",
               "UR": "R", "UG": "U", "BR": "B", "BG": "G", "RG": "R"}
    colored = Counter(c for c in cost if c.isalpha())
    total = sum(colored.values()) + int("".join(c for c in cost if c.isdigit()) or 0)
    selected_count = min(turn, len(lands))
    if total > selected_count:
        return False
    types = set("".join(s.types for s in lands))
    for battlefield in combinations(lands, selected_count):
        options = [s.colors if s.kind != "verge" or types.intersection(s.colors) else primary[s.colors]
                   for s in battlefield]
        if any(all(assignment.count(c) >= n for c, n in colored.items()) for assignment in product(*options)):
            return True
    return False


class VergeTests(unittest.TestCase):
    def test_lookup_and_source_validation(self):
        for pair, name, primary, secondary in (("UB", "Gloomlake Verge", "U", "B"),
                                                ("BG", "Wastewood Verge", "G", "B"),
                                                ("UG", "Willowrush Verge", "U", "G")):
            rule = VERGE_RULES[pair]
            self.assertEqual((rule.name, rule.primary, rule.secondary, rule.requires),
                             (name, primary, secondary, pair))
            self.assertEqual(ManaSource(pair, "verge").primary_colors, primary)
        self.assertEqual(ManaSource("U", "basic").types, "U")
        self.assertEqual(ManaSource("BU", "shock", "BU"), ManaSource("UB", "shock", "UB"))
        self.assertEqual(ManaSource("UB", "shock").types, "")
        for colors, kind, types in (("U", "verge", ""), ("UB", "verge", "U"),
                                    ("WUBRG", "town", "U"), ("UB", "shock", "U"),
                                    ("UB", "shock", "GG"), ("U", "basic", "B")):
            with self.assertRaises(ValueError):
                ManaSource(colors, kind, types)

    def test_unconditional_colors_and_enablers(self):
        for pair, primary, secondary in (("WU", "W", "U"), ("WB", "B", "W"), ("WR", "W", "R"),
                                         ("WG", "G", "W"), ("UB", "U", "B"), ("UR", "R", "U"),
                                         ("UG", "U", "G"), ("BR", "B", "R"), ("BG", "G", "B"),
                                         ("RG", "R", "G")):
            verge = ManaSource(pair, "verge")
            for color, expected in ((primary, 1), (secondary, 0)):
                row = evaluate({verge: 1}, [SpellCost(color, 1)], turns=1).opportunities[-1]
                self.assertEqual(row.expected_copies, expected)
            for enabling_type in pair:
                base = {verge: 2, ManaSource(enabling_type, "basic"): 1}
                result = evaluate(base, [SpellCost(secondary * 2, 1)], turns=3)
                self.assertEqual(result.opportunities[-1].expected_copies, 1)

    def test_enablers_anywhere_seen_unlock_colors(self):
        verge = ManaSource("UB", "verge")
        for shock, expected in ((ManaSource("UG", "shock", "UG"), 1),
                               (ManaSource("UG", "shock"), 0)):
            result = evaluate({verge: 2, shock: 1}, [SpellCost("BB", 1)], turns=3)
            self.assertTrue(all(r.expected_copies == 0 for r in result.opportunities if r.turn == 1))
            self.assertTrue(all(r.expected_copies == expected for r in result.opportunities if r.turn == 2))
            self.assertEqual(result.opportunities[-1].expected_copies, expected)
        # A typed enabler may also supply mana in the same payment.
        result = evaluate({verge: 1, ManaSource("UG", "shock", "UG"): 1},
                          [SpellCost("BU", 1)], turns=2)
        self.assertEqual(result.opportunities[-1].expected_copies, 1)

    def test_town_cavern_and_verges_do_not_enable(self):
        verge = ManaSource("UB", "verge")
        for other in (ManaSource("WUBRG", "town"), ManaSource("WUBRG", "cavern"), ManaSource("BG", "verge")):
            result = evaluate({verge: 2, other: 1}, [SpellCost("BB", 1)], turns=3)
            self.assertEqual(result.opportunities[-1].expected_copies, 0)

    def test_against_physical_draws_and_assignments(self):
        bases = [
            {ManaSource("UB", "verge"): 2, ManaSource("UG", "shock", "UG"): 1},
            {ManaSource("BG", "verge"): 1, ManaSource("UG", "verge"): 1,
             ManaSource("B", "basic"): 1, ManaSource("WUBRG", "town"): 1},
            {ManaSource(c, "verge"): 1 for c in ("UB", "UG", "BG")} |
            {ManaSource(c, "basic"): 1 for c in "UBG"},
            {ManaSource("UB", "verge"): 1, ManaSource("UG", "shock", "UG"): 1,
             ManaSource("UG", "shock"): 1, ManaSource("WUBRG", "town"): 1},
        ]
        bases += [{ManaSource(pair, "verge"): 2, ManaSource(pair[0], "basic"): 1}
                  for pair in ("WU", "WB", "WR", "WG", "UR", "BR", "RG")]
        spells = [SpellCost("BB", 2), SpellCost("1G", 1), SpellCost("UB", 1)]
        for base in bases:
            deck = [s for s, n in base.items() for _ in range(n)]
            deck += [s.cost for s in spells for _ in range(s.count)]
            for opening in (0, 2, 20):
                result = evaluate(base, spells, turns=3, opening_hand_size=opening)
                for row in result.opportunities:
                    seen = min(len(deck), opening + row.turn - (row.position == "play"))
                    successes = 0
                    for indices in combinations(range(len(deck)), seen):
                        hand = [deck[i] for i in indices]
                        lands = [s for s in hand if isinstance(s, ManaSource)]
                        if can_pay_physical(lands, row.cost, row.turn):
                            successes += hand.count(row.cost)
                    self.assertEqual(row.expected_copies, Fraction(successes, comb(len(deck), seen)), row)

    def test_unconditional_fast_path_regression(self):
        base = {ManaSource("UB", "shock"): 2, ManaSource("U", "basic"): 1}
        typed = {ManaSource("UB", "shock", "UB"): 2, ManaSource("U", "basic"): 1}
        spells = [SpellCost("UU", 2), SpellCost("1B", 1)]
        self.assertEqual(evaluate(base, spells), evaluate(typed, spells))
        base[ManaSource("UB", "verge")] = 0
        self.assertEqual(evaluate(base, spells), evaluate(typed, spells))
        # Generic/zero costs remain valid with actual conditional sources.
        result = evaluate({ManaSource("UB", "verge"): 2}, [SpellCost("0", 1), SpellCost("2", 1)], turns=2)
        self.assertTrue(all(r.expected_copies == 1 for r in result.opportunities if r.cost == "0"))
        self.assertEqual(result.opportunities[-1].expected_copies, 1)

    def test_component_tables_and_mode_weights(self):
        v, d = ManaSource("UB", "verge"), ManaSource("UG", "shock", "UG")
        space = ManaSpace({v: (0, 3), d: (0, 3)}, 3)
        spells = [Spell(2, (CastingMode("BB"), CastingMode("UU")), weight=2)]
        full = build_component_table(space, spells, turns=3, opening_hand_size=2)
        for row in full.rank(shock_penalty=0.1):
            expected = evaluate(dict(zip(space.sources, row.counts)), spells,
                                turns=3, opening_hand_size=2, shock_penalty=0.1)
            self.assertAlmostEqual(float(row.score), expected.score)
        full.crossings("BB")

    def test_expanded_source_pool_includes_zero_count_verges(self):
        base = {ManaSource(c, "basic"): n for c, n in (("U", 4), ("B", 4), ("G", 2))}
        base.update({ManaSource(c, "shock", c): 4 for c in ("UB", "UG", "BG")})
        base[ManaSource("WUBRG", "town")] = 4
        base.update({ManaSource(c, "verge"): 0 for c in ("UB", "UG", "BG")})
        caps = {"basic": 5, "shock": 4, "town": 8, "verge": 4}
        space = ManaSpace({s: (0, caps[s.kind]) for s in base}, 26)
        self.assertEqual(space.candidate_count(), 2040499)
        counts = space.counts(base)
        for verge in (s for s in space.sources if s.kind == "verge"):
            self.assertEqual(counts[space.sources.index(verge)], 0)
            self.assertEqual(space.bounds[verge], (0, 4))



if __name__ == "__main__":
    unittest.main()
