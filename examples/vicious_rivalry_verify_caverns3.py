"""Budgeted two-swap verification of the saved h=1.5 three-Cavern base."""
import argparse
import json
import pickle
from pathlib import Path

from examples.vicious_rivalry_sweep import COUNTS, NAMES, SPELLS, make_space
from examples.sultai import MANA_MODEL
from mtg_tools.mana.lands import ManaSource as S
from mtg_tools.mana.evaluation import evaluate
from mtg_tools.mana.evaluation import LocalManaEvaluator
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.local import local_search


def run(budget=2000):
    original = make_space((0, 8))
    space = ManaSpace({**original.bounds, S('WUBRG', 'cavern'): (3, 3),
                       **{S(p, 'typed_tapped'): (0, 2) for p in ('UB', 'BG', 'UG')}},
                      26, {**original.family_bounds, 'basic': (1, 2), 'typed_tapped': (2, 2)})
    ev = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, half_life=1.5)
    for path in (Path('.cache/rivalry_h1_5_caverns3_one_swap.pkl'),
                 Path('.cache/rivalry_h1_5_caverns3_two_swap.pkl')):
        if path.exists():
            with path.open('rb') as f:
                sig, entries = pickle.load(f)
            ev.restore_cache(sig, entries)
    seed = json.loads(Path('ideas/reports/vicious_rivalry_h1_5_caverns3_one_swap.json').read_text())
    inverse = {NAMES[s]: s for s in space.sources}
    base = {inverse[k]: v for k, v in seed['lands'].items()}
    one = ev.neighbor_counts(base, max_replacements=1)
    two = ev.neighbor_counts(base, max_replacements=2)
    before = len(ev.cache)
    report = {'half_life': 1.5, 'caverns': 3, 'max_replacements': 2, 'budget': budget,
              'baseline_score': seed['score'], 'baseline_lands': seed['lands'],
              'initial_one_swap_neighbors': len(one), 'initial_two_swap_neighbors': len(two),
              'initial_uncached_neighbors': sum(c not in ev.cache for c in two),
              'family_bounds': dict(space.family_bounds), 'spell_counts': COUNTS,
              'source_bounds': {NAMES[s]: list(b) for s, b in space.bounds.items()}}
    stem = Path('ideas/reports/vicious_rivalry_h1_5_caverns3_two_swap')

    def checkpoint(visits, best):
        lands = {NAMES[s]: n for s, n in zip(space.sources, best.counts) if n}
        report.update(visits=visits, score=float(best.score), exact_score=str(best.score),
                      lands=lands, stop='running', new_evaluations=len(ev.cache) - before)
        stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
        stem.with_suffix('.txt').write_text('Deck\n' + '\n'.join(
            f'{n} {name}' for name, n in {**COUNTS, **lands}.items()) + '\n')
        print(f'visits={visits} score={float(best.score):.12f} lands={lands}', flush=True)

    print(json.dumps(report), flush=True)
    result = local_search(ev, base, evaluation_budget=budget, max_replacements=2, progress=checkpoint)
    winning_base = dict(zip(space.sources, result.best.counts))
    space.counts(winning_base)
    assert abs(evaluate(winning_base, SPELLS, model=MANA_MODEL, half_life=1.5).score
               - float(result.best.score)) < 1e-12
    report.update(stop=result.stopped, seconds=result.seconds,
                  moves=[{'score': float(m.score),
                          'removed': {NAMES[s]: n for s, n in m.swap.out},
                          'added': {NAMES[s]: n for s, n in m.swap.incoming}}
                         for m in result.moves])
    stem.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    with Path('.cache/rivalry_h1_5_caverns3_two_swap.pkl').open('wb') as f:
        pickle.dump((ev.cache_signature, dict(ev.cache)), f)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget', type=int, default=2000)
    run(parser.parse_args().budget)
