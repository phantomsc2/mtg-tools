import unittest
from collections import Counter
from fractions import Fraction as F
from itertools import combinations, product
from math import comb, prod
from unittest.mock import Mock

from mtg_tools.mana_lands import ManaSource
from mtg_tools.mana_model import ManaContext, ManaModel, ManaOutcome, heuristic_mana_model
from mtg_tools.mana_opportunities import SpellCost, evaluate
from mtg_tools.mana_search import LocalManaEvaluator, ManaSpace, build_component_table


def physical_expectation(base, cost, model, turn, seen):
    """Enumerate draws, realized outcomes, and mana choices independently of the DPs."""
    deck = [source for source, n in base.items() for _ in range(n)] + [cost]
    colored = Counter(c for c in cost if c in "WUBRG")
    total = sum(colored.values()) + int(cost.rstrip("WUBRG") or 0)
    limit = model.source_limit(turn)
    if limit is not None and total > limit:
        return F()
    success = F()
    for indices in combinations(range(len(deck)), seen):
        hand = [deck[i] for i in indices]
        if cost not in hand:
            continue
        lands = [s for s in hand if isinstance(s, ManaSource)]
        context = ManaContext(turn, "".join(c for c in "WUBRG" if any(c in s.types for s in lands)))
        for outcomes in product(*(model.outcomes(s, context) for s in lands)):
            probability = prod(outcome.probability for outcome in outcomes)
            if any(sum(bool(bundle) for bundle in choices) >= total
                   and all("".join(choices).count(c) >= n for c, n in colored.items())
                   for choices in product(*(outcome.options for outcome in outcomes))):
                success += probability
    return success / comb(len(deck), seen)


class ManaModelTests(unittest.TestCase):
    def test_outcome_choices_and_validation(self):
        self.assertEqual(ManaOutcome(1, ("B", "U", "U", "")), ManaOutcome(F(1), ("U", "B")))
        for probability, options in ((-1, ("U",)), (2, ("U",)), (float("nan"), ("U",)),
                                     (1, ()), (1, ("UU",)), (1, ("C",))):
            with self.subTest(probability=probability, options=options), self.assertRaises(ValueError):
                ManaOutcome(probability, options)
        source = ManaSource("U", "basic")
        decimal = heuristic_mana_model(availability=lambda s, t: 0.7).compile((source,), 1)
        self.assertEqual({outcome.probability for outcome in decimal.turns[0][1][0][0]}, {F(7, 10), F(3, 10)})
        duplicate = ManaModel(lambda s, c: (ManaOutcome(F(1, 4), ("U",)), ManaOutcome(F(3, 4), ("U",))),
                              lambda t: t)
        self.assertEqual(duplicate.compile((source,), 1).signature,
                         heuristic_mana_model().compile((source,), 1).signature)
        for outcomes in ((), (ManaOutcome(F(1, 2), ("U",)),), ("U",)):
            with self.assertRaises(ValueError):
                ManaModel(lambda s, c: outcomes, lambda t: t).compile((source,), 1)
        for limit in (-1, True, F(1, 2)):
            with self.assertRaises(ValueError):
                heuristic_mana_model(source_limit=lambda t: limit).compile((source,), 1)

    def test_joint_outcomes_against_physical_oracle(self):
        u, dual, verge = ManaSource("U", "basic"), ManaSource("UB", "shock", "UB"), ManaSource("UB", "verge")

        def outcomes(source, context):
            if source == u:
                return (ManaOutcome(F(1, 3), ("",)), ManaOutcome(F(2, 3), ("U",)))
            if source == dual:
                return (ManaOutcome(F(1, 2), ("U", "B")), ManaOutcome(F(1, 6), ("B",)),
                        ManaOutcome(F(1, 3), ("",)))
            options = ("U", "B") if "U" in context.seen_types or "B" in context.seen_types else ("U",)
            return (ManaOutcome(F(context.turn, context.turn + 1), options),
                    ManaOutcome(F(1, context.turn + 1), ("",)))

        model = ManaModel(outcomes, lambda t: None)
        base = {u: 1, dual: 1, verge: 2}
        for cost in ("0", "U", "BB", "UB", "2B", "UUUB"):
            result = evaluate(base, [SpellCost(cost, 1)], model=model, turns=3, opening_hand_size=1)
            for row in result.opportunities:
                seen = min(5, 1 + row.turn - (row.position == "play"))
                self.assertEqual(row.expected_copies, physical_expectation(base, cost, model, row.turn, seen), row)
        space = ManaSpace({source: (0, 2) for source in base}, 4)
        spells = [SpellCost(c, 1) for c in ("0", "U", "BB", "UB", "2B", "UUUB")]
        for position, opening in (("both", 1), ("play", 0), ("draw", 99)):
            args = dict(model=model, turns=3, opening_hand_size=opening, position=position)
            self.assertEqual(build_component_table(space, spells, backend="scalar", **args),
                             build_component_table(space, spells, backend="batch", **args))

    def test_unavailable_enabler_still_enables_seen_type_policy(self):
        enabler, verge = ManaSource("U", "basic"), ManaSource("UB", "verge")
        model = heuristic_mana_model(availability=lambda source, turn: F(source != enabler))
        base = {enabler: 1, verge: 1}
        result = evaluate(base, [SpellCost("B", 1)], model=model, turns=1, opening_hand_size=99)
        self.assertEqual(result.opportunities[0].expected_copies, 1)
        result = evaluate(base, [SpellCost("UB", 1)], model=model, turns=2, opening_hand_size=99)
        self.assertTrue(all(row.expected_copies == 0 for row in result.opportunities))

    def test_explicit_model_limits_and_cache_isolation(self):
        source = ManaSource("U", "basic")
        base, spells = {source: 2}, [SpellCost("UU", 1), SpellCost("0", 1)]
        for limit, expected in ((0, 0), (1, 0), (2, 1), (None, 1)):
            model = heuristic_mana_model(source_limit=lambda turn: limit)
            args = dict(model=model, turns=1, opening_hand_size=99)
            self.assertEqual(evaluate(base, spells, **args).opportunities[0].expected_copies, expected)
            space = ManaSpace({source: (2, 2)}, 2)
            table = build_component_table(space, spells, **args)
            scalar = build_component_table(space, spells, backend="scalar", **args)
            self.assertEqual(table, scalar)
            self.assertEqual(evaluate(base, spells, **args).opportunities[2].expected_copies, 1)
        with self.assertRaises(TypeError):
            evaluate(base, spells)
        full = heuristic_mana_model(availability=lambda s, t: F(1))
        absent = heuristic_mana_model(availability=lambda s, t: F(0))
        self.assertNotEqual(full.compile((source,), 2).signature, absent.compile((source,), 2).signature)
        self.assertEqual(full.compile((source,), 2).signature, heuristic_mana_model().compile((source,), 2).signature)
        space = ManaSpace({source: (2, 2)}, 2)
        one = LocalManaEvaluator(space, spells, model=full, turns=2)
        zero = LocalManaEvaluator(space, spells, model=absent, turns=2)
        self.assertGreater(one.components(base).score, zero.components(base).score)
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            zero.restore_cache(one.cache_signature, dict(one.cache))
        other = LocalManaEvaluator(space, spells, model=heuristic_mana_model(), turns=2)
        other.restore_cache(one.cache_signature, dict(one.cache))
        self.assertEqual(other.components(base), one.components(base))
        changed = LocalManaEvaluator(space, spells, model=full, turns=2, opening_hand_size=1)
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            changed.restore_cache(one.cache_signature, dict(one.cache))

    def test_local_model_is_compiled_once(self):
        callback = Mock(return_value=(ManaOutcome(F(1), ("U",)),))
        source = ManaSource("U", "basic")
        model = ManaModel(callback, lambda t: None)
        evaluator = LocalManaEvaluator(ManaSpace({source: (0, 2)}, 2), [SpellCost("U", 1)], model=model)
        calls = callback.call_count
        evaluator.components({source: 2})
        evaluator.components({source: 2})
        self.assertEqual(callback.call_count, calls)


if __name__ == "__main__":
    unittest.main()
