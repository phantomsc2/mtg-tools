"""Bounded one-swap searches with four Caverns and two fixed Undercity Sewers."""
import argparse
import json
import pickle
from pathlib import Path
from time import perf_counter

from examples.vicious_rivalry_sweep import COUNTS, NAMES, SPELLS, make_space
from examples.sultai import MANA_MODEL
from mtg_tools.mana_lands import ManaSource as S
from mtg_tools.mana_opportunities import evaluate
from mtg_tools.mana_search import LocalManaEvaluator, ManaSpace, local_search


def run(h, budget=800):
    started = perf_counter()
    original = make_space((0, 8))
    sewers = S('UB', 'typed_tapped')
    space = ManaSpace({**original.bounds, sewers: (2, 2)}, 26,
                      {**original.family_bounds, 'basic': (1, 2), 'typed_tapped': (2, 2)})
    ev = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, half_life=h)
    tag = str(h).replace('.', '_')
    stem = Path(f'ideas/reports/vicious_rivalry_h{tag}_fixed_sewers_one_swap')
    cache = Path(f'.cache/rivalry_h{tag}_fixed_sewers_one_swap.pkl')
    if cache.exists():
        with cache.open('rb') as f:
            signature, entries = pickle.load(f)
        ev.restore_cache(signature, entries)
    inverse = {NAMES[s]: s for s in space.sources}
    seeds = []
    # Compare all three previous winning compositions after replacing the tapped
    # slots, then descend from the strongest. No expensive duplicate starts.
    for previous_h in (1.0, 1.5, 2.0):
        previous_tag = str(previous_h).replace('.', '_')
        previous = json.loads(Path(
            f'ideas/reports/vicious_rivalry_h{previous_tag}_typed_basic1_one_swap.json').read_text())
        base = {inverse[n]: c for n, c in previous['lands'].items() if n != 'Hedge Maze'}
        base[sewers] = 2
        space.counts(base)
        value = ev.value(base)
        seeds.append((value, previous_h, base))
    best_seed, seed_h, initial = max(seeds, key=lambda item: item[0].score)
    report = {'half_life': h, 'horizon': ev.timing.horizon, 'max_replacements': 1,
              'budget': budget, 'spell_counts': COUNTS,
              'family_bounds': dict(space.family_bounds),
              'source_bounds': {NAMES[s]: list(b) for s, b in space.bounds.items()},
              'seeds': [{'previous_h': sh, 'score': float(v.score),
                         'lands': {NAMES[s]: n for s, n in b.items() if n}}
                        for v, sh, b in seeds],
              'selected_seed_h': seed_h, 'seed_score': float(best_seed.score),
              'assumptions': ['Exactly two Undercity Sewers; other typed tapped duals excluded.',
                              'One-swap only; no global or two-swap certificate.',
                              'Cavern unrestricted; no sequencing, life totals, surveil or land abilities.']}

    def checkpoint(visits, best):
        lands = {NAMES[s]: n for s, n in zip(space.sources, best.counts) if n}
        report.update(visits=visits, score=float(best.score), exact_score=str(best.score),
                      lands=lands, stop='running', elapsed_seconds=perf_counter()-started)
        stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
        stem.with_suffix('.txt').write_text('\n'.join(f'{n} {name}' for name, n in lands.items()) + '\n')
        print(f'h={h} visits={visits} score={float(best.score):.12f} lands={lands}', flush=True)

    result = local_search(ev, initial, evaluation_budget=budget, max_replacements=1, progress=checkpoint)
    base = dict(zip(space.sources, result.best.counts))
    space.counts(base)
    assert abs(evaluate(base, SPELLS, model=MANA_MODEL, half_life=h).score
               - float(result.best.score)) < 1e-12
    report.update(stop=result.stopped, search_seconds=result.seconds,
                  elapsed_seconds=perf_counter()-started, unique_evaluations=len(ev.cache))
    stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    with cache.open('wb') as f:
        pickle.dump((ev.cache_signature, dict(ev.cache)), f)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--half-life', type=float, choices=(1, 1.5, 2), required=True)
    parser.add_argument('--budget', type=int, default=800)
    args = parser.parse_args()
    run(args.half_life, args.budget)
