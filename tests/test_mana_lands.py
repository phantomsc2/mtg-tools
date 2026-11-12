import unittest
from collections import Counter
from itertools import combinations

from mtg_tools.mana_lands import COLORS, ManaSource, VERGE_RULES, sources_for_colors
from mtg_tools.mana_model import heuristic_mana_model
from mtg_tools.mana_opportunities import SpellCost
from mtg_tools.mana_search import ManaSpace, build_component_table

MODEL = heuristic_mana_model()


class LandPoolTests(unittest.TestCase):
    def test_selected_colors_and_families(self):
        families = {"basic": (0, 3), "shock": (0, 4), "verge": (0, 4)}
        for colors in ("R", "RW", "RWB", "WUBRG"):
            space = ManaSpace.from_colors(2, colors, families=families)
            pairs = len(tuple(combinations(colors, 2)))
            self.assertEqual(Counter(s.kind for s in space.sources),
                             Counter({"basic": len(colors), "shock": pairs, "verge": pairs}))
            for source in space.sources:
                self.assertLessEqual(set(source.colors), set(colors))
                self.assertEqual(source.types, source.colors if source.kind != "verge" else "")
        self.assertEqual(ManaSpace.from_colors(2, "RW", families=families),
                         ManaSpace.from_colors(2, "WR", families=dict(reversed(list(families.items())))))

    def test_explicit_rainbows_and_overrides(self):
        space = ManaSpace.from_colors(4, "U", families={"town": (0, 4), "cavern": (0, 4)})
        self.assertEqual({s.kind for s in space.sources}, {"town", "cavern"})
        self.assertTrue(all(s.colors == COLORS and not s.types for s in space.sources))
        source = ManaSource("WR", "shock", "WR")
        space = ManaSpace.from_colors(2, "WR", families={"shock": (0, 4), "basic": (0, 2)},
                                      overrides={source: (1, 1)})
        self.assertEqual(space.bounds[source], (1, 1))
        self.assertEqual(space.candidate_count(), 2)
        self.assertTrue(all(counts[space.sources.index(source)] == 1 for counts in space.exhaustive()))
        self.assertEqual(sources_for_colors("WR", ["verge"]), (ManaSource("WR", "verge"),))

    def test_invalid_configuration(self):
        for colors in ("", "WW", "UX", None):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                ManaSpace.from_colors(1, colors, families={"basic": (0, 2)})
        for families in ({"fetch": (0, 4)}, {"basic": (2, 1)}, {"shock": (-1, 4)},
                         {"shock": (0, True)}, {"shock": (0, 1, 2)}, {}):
            with self.subTest(families=families), self.assertRaises(ValueError):
                ManaSpace.from_colors(1, "U", families=families)
        for source in (ManaSource("B", "basic"), ManaSource("WU", "shock")):
            with self.assertRaises(ValueError):
                ManaSpace.from_colors(1, "WU", families={"basic": (0, 2), "shock": (0, 4)},
                                      overrides={source: (0, 1)})
        with self.assertRaises(ValueError):
            ManaSpace.from_colors(5, "WR", families={"shock": (0, 4)})
        self.assertEqual(ManaSpace.from_colors(0, "U", families={}).candidate_count(), 1)

    def test_complete_verge_card_data(self):
        expected = {
            "WU": ("Floodfarm", "W", "U"), "WB": ("Bleachbone", "B", "W"),
            "WR": ("Sunbillow", "W", "R"), "WG": ("Hushwood", "G", "W"),
            "UB": ("Gloomlake", "U", "B"), "UR": ("Riverpyre", "R", "U"),
            "UG": ("Willowrush", "U", "G"), "BR": ("Blazemire", "B", "R"),
            "BG": ("Wastewood", "G", "B"), "RG": ("Thornspire", "R", "G"),
        }
        self.assertEqual(set(VERGE_RULES), set(expected))
        for pair, (name, primary, secondary) in expected.items():
            rule = VERGE_RULES[pair]
            self.assertEqual((rule.name, rule.primary, rule.secondary, rule.requires),
                             (name + " Verge", primary, secondary, pair))

    def test_generated_pools_batch_equal_scalar(self):
        for colors in ("WU", "WB", "WR", "WG", "UR", "BR", "RG"):
            with self.subTest(colors=colors):
                space = ManaSpace.from_colors(2, colors,
                    families={"basic": (0, 1), "shock": (0, 1), "verge": (0, 2)})
                spells = [SpellCost(c * 2, 1) for c in colors] + [SpellCost(colors, 1)]
                options = dict(turns=2, opening_hand_size=2)
                scalar = build_component_table(space, spells, model=MODEL, backend="scalar", **options)
                batch = build_component_table(space, spells, model=MODEL, backend="batch", **options)
                self.assertEqual(scalar, batch)

    def test_standard_snapshot_filters_families_before_bounds(self):
        space = ManaSpace.from_colors(26, "UBG", format="standard",
                    families={kind:(0,4) for kind in ("shock","fast","verge","town","cavern")})
        self.assertEqual({s.colors for s in space.sources if s.kind=="fast"}, {"UG","BG"})
        self.assertEqual(len(space.sources),10)
        self.assertEqual(len(sources_for_colors("WUBRG", ["fast"], format="standard")),5)
        self.assertEqual(sources_for_colors("UB", ["slow"], format="standard"),())
        self.assertEqual(len(sources_for_colors("UBG", ["fast"])),3)
        with self.assertRaises(ValueError):
            ManaSpace.from_colors(26,"UBG",format="standard",families={"shock":(0,4),"fast":(0,4)},
                                 overrides={ManaSource("UB","fast"):(0,4)})
        with self.assertRaises(ValueError):
            sources_for_colors("UB",["fast"],format="unknown")

    def test_fixed_sources_inside_and_outside_families(self):
        swamp = ManaSource("B", "basic")
        cavern = ManaSource("WUBRG", "cavern")
        space = ManaSpace.from_colors(7, "UB", families={"basic":(0,2)},
                                      fixed={swamp:3, cavern:4})
        self.assertEqual(space.bounds[swamp], (3,3))
        self.assertEqual(space.bounds[cavern], (4,4))
        self.assertEqual(space.candidate_count(), 1)
        for counts in space.exhaustive():
            self.assertEqual(counts[space.sources.index(swamp)], 3)
            self.assertEqual(counts[space.sources.index(cavern)], 4)
            self.assertEqual(sum(counts), 7)
        zero = ManaSpace.from_colors(2, "UB", families={"basic":(0,2)}, fixed={swamp:0})
        self.assertEqual(zero.candidate_count(), 1)
        self.assertEqual(zero.bounds[swamp], (0,0))
        fixed_only = ManaSpace.from_colors(5, "B", families={}, fixed={swamp:1, cavern:4})
        self.assertEqual(fixed_only.candidate_count(), 1)
        self.assertEqual(fixed_only.counts({swamp:1, cavern:4}), next(fixed_only.exhaustive()))

    def test_invalid_fixed_sources_counts_and_conflicts(self):
        swamp = ManaSource("B", "basic")
        for fixed in ({swamp:-1}, {swamp:True}, {swamp:1.5}, {"Swamp":1},
                      {ManaSource("R","basic"):1}, {ManaSource("UB","fast"):1}):
            with self.subTest(fixed=fixed), self.assertRaises(ValueError):
                ManaSpace.from_colors(2,"UB",families={"basic":(0,2)},format="standard",fixed=fixed)
        with self.assertRaisesRegex(ValueError, "both fixed"):
            ManaSpace.from_colors(2,"UB",families={"basic":(0,2)},fixed={swamp:1},overrides={swamp:(0,2)})
        for total,fixed in ((1,{swamp:2}),(3,{swamp:2})):
            with self.assertRaises(ValueError):
                ManaSpace.from_colors(total,"B",families={},fixed=fixed)

    def test_fixed_draw_counts_batch_agree_with_scalar(self):
        swamp = ManaSource("B", "basic")
        cavern = ManaSource("WUBRG", "cavern")
        space = ManaSpace.from_colors(4,"UB",format="standard",families={"shock":(0,2),"verge":(0,2)},
                                      fixed={swamp:1,cavern:1})
        spells = [SpellCost("BB",2),SpellCost("UU",1),SpellCost("W",1)]
        args = dict(turns=3,opening_hand_size=2)
        scalar = build_component_table(space,spells, model=MODEL,backend="scalar",**args)
        self.assertEqual(scalar,build_component_table(space,spells, model=MODEL,backend="batch",**args))
        self.assertTrue(all(row.counts[space.sources.index(swamp)] == 1 and
                            row.counts[space.sources.index(cavern)] == 1 for row in scalar.rows))

    def test_notebook_fixed_pool_size_and_every_candidate(self):
        fixed = {ManaSource("WUBRG","cavern"):4, ManaSource("B","basic"):1}
        space = ManaSpace.from_colors(26,"UBG",format="standard",fixed=fixed,
                                      families={k:(0,4) for k in ("shock","fast","verge","town")})
        self.assertEqual(space.candidate_count(), 142740)
        indices = [(space.sources.index(source), n) for source,n in fixed.items()]
        self.assertTrue(all(sum(counts)==26 and all(counts[i]==n for i,n in indices)
                            for counts in space.exhaustive()))
