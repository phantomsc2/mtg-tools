import unittest
from fractions import Fraction as F
from random import Random
from unittest.mock import patch

from mana_lands import ManaSource
from mana_search import BaseComponents, ComponentTable, Interval, ManaSpace


def interval_oracle(lines, index):
    a, b = lines[index]
    lower, upper = F(0), None
    for aa, bb in lines:
        if bb == b:
            if aa > a:
                return None
        elif bb > b:
            bound = (a - aa) / (bb - b)
            upper = bound if upper is None else min(upper, bound)
        else:
            lower = max(lower, (a - aa) / (bb - b))
    return None if upper is not None and upper < lower else Interval(lower, upper)


class ReportingTests(unittest.TestCase):
    def table(self):
        rng = Random(42)
        space = ManaSpace({ManaSource(c, "basic"): (0, 8) for c in "UBG"}, 8)
        rows = tuple(BaseComponents(counts, tuple(F(rng.randrange(50), rng.randrange(1, 20)) for _ in range(3)),
                                    rng.randrange(9), rng.randrange(9)) for counts in space.exhaustive())
        return ComponentTable(space, ("U", "B", "G"), (F(1), F(1), F(1)), rows)

    def test_rank_and_crossings_against_fraction_oracle(self):
        table = self.table()
        for weights, shock, town in (((F(1), F(1), F(1)), F(1, 100), F(1, 100)),
                                      ((F(0), F(2, 3), F(1, 7)), F(0), F(3, 20)),
                                      ((F(2, 5), F(3, 7), F(1, 11)), F(1, 3), F(0))):
            scored = table.score(dict(zip(table.costs, weights)), shock_penalty=shock, town_penalty=town)
            raw = [sum((v * w for v, w in zip(row.opportunities, weights)), F()) for row in table.rows]
            scores = [r - row.shock_count * shock - row.town_count * town for r, row in zip(raw, table.rows)]
            order = sorted(range(len(scores)), key=lambda i: (-scores[i], table.rows[i].counts))
            for limit in (0, 1, 5, len(scores) + 2, None):
                ranked = scored.rank(limit=limit)
                expected = order if limit is None else order[:limit]
                self.assertEqual([r.counts for r in ranked], [table.rows[i].counts for i in expected])
                self.assertEqual([r.score for r in ranked], [scores[i] for i in expected])
                self.assertEqual([r.raw_score for r in ranked], [raw[i] for i in expected])
            for parameter in (*table.costs, "shock_penalty", "town_penalty"):
                if parameter in table.costs:
                    j = table.costs.index(parameter)
                    current = weights[j]
                    slopes = [r.opportunities[j] for r in table.rows]
                else:
                    current = shock if parameter == "shock_penalty" else town
                    slopes = [F(-getattr(r, parameter.replace("penalty", "count"))) for r in table.rows]
                lines = [(score - slope * current, slope) for score, slope in zip(scores, slopes)]
                for reference_index in (order[0], 0):
                    reference = table.rows[reference_index].counts
                    result = scored.crossings(parameter, baseline=dict(zip(table.space.sources, reference)))
                    expected_interval = interval_oracle(lines, reference_index)
                    self.assertEqual(result.optimal_interval, expected_interval)
                    self.assertEqual(result.baseline_is_optimal, scores[reference_index] == scores[order[0]])
                    if not result.baseline_is_optimal:
                        self.assertIsNone(result.lower)
                        self.assertIsNone(result.upper)
                        continue
                    for transition, direction, value in ((result.lower, -1, expected_interval.lower),
                                                          (result.upper, 1, expected_interval.upper)):
                        if value is None or (direction == -1 and value == 0):
                            self.assertIsNone(transition)
                            continue
                        best = max(a + b * value for a, b in lines)
                        tied = [i for i, (a, b) in enumerate(lines) if a + b * value == best]
                        winner = min(tied, key=lambda i: (-direction * slopes[i],
                                     sum(abs(a - b) for a, b in zip(reference, table.rows[i].counts)),
                                     table.rows[i].counts))
                        self.assertEqual(transition.value, value)
                        self.assertEqual(transition.counts, table.rows[winner].counts)
                        self.assertEqual(transition.optimal_interval, interval_oracle(lines, winner))

    def test_snapshot_reuse_and_only_displayed_swap_objects(self):
        table = self.table()
        scored = table.score(shock_penalty=F(1, 100), town_penalty=F(1, 100))
        original = ComponentTable._swap
        with patch.object(ComponentTable, "score", side_effect=AssertionError("Repeated scoring")):
            with patch.object(ComponentTable, "_swap", autospec=True, side_effect=original) as swap:
                top = scored.rank(limit=5, baseline=dict(zip(table.space.sources, table.rows[0].counts)))
                self.assertEqual(swap.call_count, 5)
                winner = dict(zip(table.space.sources, top[0].counts))
                for parameter in ("shock_penalty", "town_penalty"):
                    result = scored.crossings(parameter, baseline=winner)
                    self.assertFalse(hasattr(result, "comparisons"))
                self.assertLessEqual(swap.call_count, 9)
        with self.assertRaises(ValueError):
            scored.rank(limit=-1)

    def test_reference_comparisons_are_query_local(self):
        table = self.table()
        scored = table.score()
        absolute = scored.rank()
        self.assertFalse(hasattr(table, "baseline"))
        self.assertTrue(all(row.delta is None and row.swap is None for row in absolute))
        winner = absolute[0].counts
        self.assertEqual(scored.crossings("U").baseline, winner)
        for counts in (table.rows[0].counts, winner):
            base = dict(zip(table.space.sources, counts))
            compared = scored.rank(baseline=base)
            score = next(row.score for row in absolute if row.counts == counts)
            self.assertEqual([row.counts for row in compared], [row.counts for row in absolute])
            self.assertEqual([row.delta for row in compared], [row.score-score for row in absolute])
            self.assertEqual(compared, table.rank(baseline=base))
            self.assertTrue(all(row.swap == table._swap(counts, row.counts) for row in compared))
        self.assertEqual(scored.rank(), absolute)
        self.assertEqual(scored.crossings("U").baseline, winner)
        with self.assertRaises(ValueError):
            scored.rank(baseline={ManaSource("R", "basic"):8})


if __name__ == "__main__":
    unittest.main()
