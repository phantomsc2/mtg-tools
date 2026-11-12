"""Revised Rivalry deck: fixed two to four Sewers, one-swap only."""
import argparse
from dataclasses import replace
from itertools import combinations_with_replacement
import json
import pickle
from pathlib import Path
from time import perf_counter

from examples.vicious_rivalry_sweep import COUNTS as PREVIOUS_COUNTS, NAMES, SPELLS as PREVIOUS_SPELLS, make_space
from examples.sultai import MANA_MODEL
from mana_lands import ManaSource as S
from mana_opportunities import evaluate, spell_components
from mana_search import LocalManaEvaluator, ManaSpace, local_search


COUNTS = {**PREVIOUS_COUNTS, 'Emptiness': 4, 'Sunderflock': 4,
          'Awaken the Honored Dead': 2, "Glarb, Calamity's Augur": 1}
# Same casting modes; update the four physical card counts from the supplied list.
SPELLS = tuple(replace(s, count={2: 4, 6: 4, 7: 2, 8: 1}.get(i, s.count))
               for i, s in enumerate(PREVIOUS_SPELLS))
USER_LANDS = {'Watery Grave': 4, 'Cavern of Souls': 4, 'Starting Town': 4,
              'Gloomlake Verge': 1, 'Breeding Pool': 4, 'Wastewood Verge': 2,
              'Deathcap Glade': 2, 'Swamp': 1, 'Shipwreck Marsh': 1,
              'Willowrush Verge': 1, 'Undercity Sewers': 2}
assert sum(COUNTS.values()) == spell_components(SPELLS)[0] == 34
assert sum(USER_LANDS.values()) == 26


def run(sewers_count, budget=800, half_life=1.5):
    started = perf_counter()
    original = make_space((0, 8))
    sewers = S('UB', 'typed_tapped')
    space = ManaSpace({**original.bounds, sewers: (sewers_count, sewers_count)}, 26,
                      {**original.family_bounds, 'basic': (1, 2),
                       'typed_tapped': (sewers_count, sewers_count)})
    ev = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, half_life=half_life)
    inverse = {NAMES[s]: s for s in space.sources}
    supplied = {inverse[name]: n for name, n in USER_LANDS.items()}
    tag = str(float(half_life)).replace('.', '_')
    stem = Path(f'reports/rivalry_revised_h{tag}_sewers{sewers_count}_one_swap')
    cache = Path(f'.cache/rivalry_revised_h{tag}_sewers{sewers_count}_one_swap.pkl')
    if cache.exists():
        with cache.open('rb') as f:
            signature, entries = pickle.load(f)
        ev.restore_cache(signature, entries)
    seeds = []
    # Evaluate legal ways to free the required one/two extra tapped slots in the
    # supplied base. Then run only single-land descent from the best seed.
    for removed in combinations_with_replacement(tuple(s for s in supplied if s != sewers), sewers_count - 2):
        base = dict(supplied)
        base[sewers] = sewers_count
        for s in removed:
            base[s] -= 1
        try:
            space.counts(base)
        except ValueError:
            continue
        seeds.append((ev.value(base), base))
    best_seed, initial = max(seeds, key=lambda row: row[0].score)
    report = {'half_life': half_life, 'horizon': ev.timing.horizon, 'sewers': sewers_count,
              'max_replacements': 1, 'budget': budget, 'spell_counts': COUNTS,
              'spell_profiles': [{'count': s.count, 'modes': [m.cost for m in s.modes]
                                  if hasattr(s, 'modes') else [s.cost]} for s in SPELLS],
              'supplied_lands': USER_LANDS, 'legal_seeds_evaluated': len(seeds),
              'seed_score': float(best_seed.score),
              'initial_lands': {NAMES[s]: n for s, n in initial.items() if n},
              'family_bounds': dict(space.family_bounds),
              'source_bounds': {NAMES[s]: list(b) for s, b in space.bounds.items()},
              'assumptions': ['One-swap local search only, not a global certificate.',
                              'No surveil, life, sequencing or land abilities; Cavern unrestricted.']}

    def checkpoint(visits, best):
        lands = {NAMES[s]: n for s, n in zip(space.sources, best.counts) if n}
        report.update(visits=visits, score=float(best.score), exact_score=str(best.score),
                      lands=lands, stop='running', elapsed_seconds=perf_counter()-started)
        stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
        stem.with_suffix('.txt').write_text('Deck\n' + '\n'.join(
            f'{n} {name}' for name, n in {**COUNTS, **lands}.items()) + '\n')
        print(f'sewers={sewers_count} visits={visits} score={float(best.score):.12f} lands={lands}', flush=True)

    print(f'sewers={sewers_count} legal_seeds={len(seeds)} best_seed={float(best_seed.score):.12f}', flush=True)
    result = local_search(ev, initial, evaluation_budget=budget, max_replacements=1, progress=checkpoint)
    base = dict(zip(space.sources, result.best.counts))
    space.counts(base)
    assert abs(evaluate(base, SPELLS, model=MANA_MODEL, half_life=half_life).score
               - float(result.best.score)) < 1e-12
    report.update(stop=result.stopped, search_seconds=result.seconds,
                  elapsed_seconds=perf_counter()-started, unique_evaluations=len(ev.cache))
    stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    with cache.open('wb') as f:
        pickle.dump((ev.cache_signature, dict(ev.cache)), f)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sewers', type=int, choices=(2, 3, 4), required=True)
    parser.add_argument('--budget', type=int, default=800)
    parser.add_argument('--half-life', type=float, choices=(1, 1.5, 2), default=1.5)
    args = parser.parse_args()
    run(args.sewers, args.budget, args.half_life)
