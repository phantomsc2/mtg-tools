"""Bounded one-swap h=1.5 searches with exactly two or three Caverns."""
import argparse
import json
import pickle
from pathlib import Path
from time import perf_counter

from examples.vicious_rivalry_sweep import COUNTS, NAMES, SPELLS, make_space
from examples.sultai import MANA_MODEL
from mtg_tools.mana.lands import ManaSource as S
from mtg_tools.mana.evaluation import evaluate
from mtg_tools.mana.evaluation import LocalManaEvaluator
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.local import local_search


def run(caverns, budget=800):
    started = perf_counter()
    original = make_space((0, 8))
    cavern = S('WUBRG', 'cavern')
    bounds = {**original.bounds, cavern: (caverns, caverns),
              **{S(p, 'typed_tapped'): (0, 2) for p in ('UB', 'BG', 'UG')}}
    space = ManaSpace(bounds, 26, {**original.family_bounds,
                                   'basic': (1, 2), 'typed_tapped': (2, 2)})
    ev = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, half_life=1.5)
    seed_path = Path('ideas/reports/vicious_rivalry_h1_5_typed_basic1_one_swap.json')
    previous = json.loads(seed_path.read_text())
    inverse = {NAMES[s]: s for s in space.sources}
    initial = {inverse[name]: n for name, n in previous['lands'].items()}
    initial[cavern] = caverns
    # Alternate the two main Verges; preserve the total land count and shock cap.
    for i in range(4 - caverns):
        source = S(('UB', 'BG')[i % 2], 'verge')
        initial[source] = initial.get(source, 0) + 1
    stem = Path(f'ideas/reports/vicious_rivalry_h1_5_caverns{caverns}_one_swap')
    cache = Path(f'.cache/rivalry_h1_5_caverns{caverns}_one_swap.pkl')
    if cache.exists():
        with cache.open('rb') as f:
            signature, entries = pickle.load(f)
        ev.restore_cache(signature, entries)
    runs = []
    winner = None
    for pair in ('UB', 'BG', 'UG'):
        base = {s: n for s, n in initial.items() if s.kind != 'typed_tapped'}
        base[S(pair, 'typed_tapped')] = 2
        space.counts(base)
        before = len(ev.cache)
        result = local_search(ev, base, evaluation_budget=budget, max_replacements=1,
                              progress=lambda n, b: print(
                                  f'caverns={caverns} start={pair} visits={n} '
                                  f'score={float(b.score):.12f}', flush=True))
        runs.append({'start': pair, 'initial_lands': {NAMES[s]: n for s, n in base.items() if n},
                     'score': float(result.best.score), 'visits': result.evaluations,
                     'new_evaluations': len(ev.cache) - before, 'seconds': result.seconds,
                     'stop': result.stopped,
                     'lands': {NAMES[s]: n for s, n in zip(space.sources, result.best.counts) if n}})
        if winner is None or result.best.score > winner.score:
            winner = result.best
        winning_base = dict(zip(space.sources, winner.counts))
        space.counts(winning_base)
        lands = {NAMES[s]: n for s, n in winning_base.items() if n}
        report = {'schema_version': 2, 'half_life': 1.5, 'horizon': ev.timing.horizon,
                  'max_replacements': 1, 'budget_per_start': budget, 'caverns': caverns,
                  'score': float(winner.score), 'exact_score': str(winner.score), 'lands': lands,
                  'spell_counts': COUNTS, 'runs': runs, 'complete': len(runs) == 3,
                  'seed_report': str(seed_path), 'previous_four_cavern_score': previous['score'],
                  'family_bounds': dict(space.family_bounds),
                  'source_bounds': {NAMES[s]: list(b) for s, b in space.bounds.items()},
                  'elapsed_seconds': perf_counter() - started,
                  'assumptions': ['One-swap only; no global or two-swap certificate.',
                                  'Cavern unrestricted; no sequencing, life totals, surveil or land abilities.']}
        stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
        stem.with_suffix('.txt').write_text('Deck\n' + '\n'.join(
            f'{n} {name}' for name, n in {**COUNTS, **lands}.items()) + '\n')
        with cache.open('wb') as f:
            pickle.dump((ev.cache_signature, dict(ev.cache)), f)
    assert abs(evaluate(winning_base, SPELLS, model=MANA_MODEL, half_life=1.5).score
               - float(winner.score)) < 1e-12
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caverns', type=int, choices=(2, 3), required=True)
    parser.add_argument('--budget', type=int, default=800)
    args = parser.parse_args()
    run(args.caverns, args.budget)
