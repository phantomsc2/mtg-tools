"""Compare 8-10 shocks with four Towns: python -m examples.sultai_shock_sweep."""

import json
import pickle
from fractions import Fraction
from pathlib import Path
from time import perf_counter

from examples.sultai import LAND_NAMES, MANA_BASE, MANA_MODEL, SPELLS
from examples.sultai_optimize import make_space, SHOCK_PENALTY, TOWN_PENALTY
from mana_lands import ManaSource
from mana_search import LocalManaEvaluator, ManaSpace, local_search


def penalty_intervals(rows):
    """Exact upper-envelope intervals among the supplied representatives."""
    intervals = []
    for row in rows:
        low, high = Fraction(), None
        for other in rows:
            slope = row['shocks'] - other['shocks']
            if not slope:
                continue
            crossing = (Fraction(row['exact_raw']) - Fraction(other['exact_raw'])) / slope
            if slope > 0:
                high = crossing if high is None else min(high, crossing)
            else:
                low = max(low, crossing)
        intervals.append(None if high is not None and high < low else
                         {'lower': str(low), 'upper': str(high) if high is not None else None})
    return intervals


def render(report):
    rows = report['results']
    lines = ['# Sultai bases with 8-10 shocks and four Towns', '',
             'Best found at each shock count for four Awaken, two Glarb and two Dellian Fels, without Overlords or Rapid Rescue.',
             'Four Caverns, four Towns and two Restless Cottages are fixed; at most two basics total; Palace capped at two.', '',
             '| Land | 8 shocks | 9 shocks | 10 shocks |',
             '| --- | ---: | ---: | ---: |']
    for name in sorted({name for row in rows for name in row['lands']}):
        lines.append('| '+name+' | '+' | '.join(str(r['lands'].get(name, 0)) for r in rows)+' |')
    lines += ['', '| Shocks | Raw opportunities | Score at 0.012 | Shock penalty interval | Stop |',
              '| ---: | ---: | ---: | --- | --- |']
    for r in rows:
        interval = r['penalty_interval']
        text = 'never preferred' if interval is None else (
            f"{float(Fraction(interval['lower'])):.9f} to " +
            (f"{float(Fraction(interval['upper'])):.9f}" if interval['upper'] is not None else 'unbounded'))
        lines.append(f"| {r['shocks']} | {r['raw']:.9f} | {r['score']:.9f} | {text} | {r['stopped']} |")
    lines += ['', 'ASCII scoring equation:', '', '```text',
              'score = raw_opportunities - shock_count * shock_penalty - 4 * town_penalty',
              '```', '',
              'Town penalty is 0.015. Because Town count is fixed, it does not affect shock-count crossings.',
              'Intervals are exact for the reported representatives. Searches do not certify global optima.',
              'A two-land local optimum checks all legal one- and two-land replacements preserving the shock total.',
              'Restless Cottage uses the untyped tapped BG source; animation, Food, and graveyard effects are not scored.',
              'Independent joint source outcomes, unrestricted Cavern, uniform mode weights, and board scenarios are used.', '',
              f"Total runtime: {report['seconds']:.2f}s. Budget: {report['budget']} visits per shock count.", '']
    return '\n'.join(lines)


def main():
    bounds = dict(make_space().bounds)
    bounds[ManaSource('WUBRG', 'town')] = (4, 4)
    space = ManaSpace(bounds, 26)
    current = dict(MANA_BASE)
    projector = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, family_maximums={"basic": 2})
    rows, caches, signatures = [], {}, {}
    started = perf_counter()
    budget = 500
    path = Path('reports/sultai_shock_sweep.json')
    for total in range(8, 11):
        print(f'Shocks {total}: preparing start', flush=True)
        while sum(n for source, n in current.items() if source.kind == 'shock') != total:
            increasing = sum(n for source, n in current.items() if source.kind == 'shock') < total
            candidates = []
            for out, (lo, _) in space.bounds.items():
                if (out.kind == 'shock') == increasing or current.get(out, 0) <= lo:
                    continue
                for incoming, (_, hi) in space.bounds.items():
                    if (incoming.kind == 'shock') != increasing or current.get(incoming, 0) >= hi:
                        continue
                    base = dict(current)
                    base[out] -= 1
                    base[incoming] = base.get(incoming, 0)+1
                    if sum(n for source, n in base.items() if source.kind == 'basic') <= 2:
                        candidates.append(projector.value(base))
            seed = min(candidates, key=lambda r: (-r.raw_score, r.counts))
            current = dict(zip(space.sources, seed.counts))
        evaluator = LocalManaEvaluator(space, SPELLS, model=MANA_MODEL, family_totals={'shock': total},
                                       family_maximums={'basic': 2})
        result = local_search(evaluator, current, evaluation_budget=budget,
                              shock_penalty=SHOCK_PENALTY, town_penalty=TOWN_PENALTY,
                              progress=lambda n, r: print(f'  {n} visits; raw {float(r.raw_score):.9f}', flush=True))
        current = dict(zip(space.sources, result.best.counts))
        assert sum(n for s, n in current.items() if s.kind == 'shock') == total
        assert sum(current.values()) == 26
        rows.append({'shocks': total, 'raw': float(result.best.raw_score),
                     'exact_raw': str(result.best.raw_score), 'score': float(result.best.score),
                     'lands': {LAND_NAMES[s]: n for s, n in current.items() if n},
                     'evaluations': result.evaluations, 'stopped': result.stopped,
                     'seconds': result.seconds})
        caches[total] = dict(evaluator.cache)
        signatures[total] = evaluator.cache_signature
        report = {'budget': budget, 'shock_penalty': SHOCK_PENALTY, 'town_penalty': TOWN_PENALTY,
                  'seconds': perf_counter()-started, 'results': rows, 'spell_profiles': [repr(spell) for spell in SPELLS],
                  'deck_note': 'Four Awaken, two Glarb, two Dellian Fel, no Overlord or Rapid Rescue; 34 spells, 26 lands.',
                  'initial': {LAND_NAMES[source]: n for source, n in MANA_BASE.items() if n},
                  'mana_model': 'heuristic joint source outcomes; seen-type enabling; turn source limit',
                  'constraints': {'caverns': 4, 'towns': 4, 'cottages': 2, 'maximum_basics': 2, 'palace_cap': 2}}
        for row, interval in zip(rows, penalty_intervals(rows)):
            row['penalty_interval'] = interval
        path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        Path('.cache').mkdir(exist_ok=True)
        with Path('.cache/sultai_shock_sweep.pkl').open('wb') as f:
            pickle.dump({'bounds': bounds, 'components': caches, 'projector': dict(projector.cache),
                         'signatures': signatures, 'projector_signature': projector.cache_signature}, f)
    path.with_suffix('.md').write_text(render(report), encoding='utf-8')
    print(render(report), flush=True)


if __name__ == '__main__':
    main()
