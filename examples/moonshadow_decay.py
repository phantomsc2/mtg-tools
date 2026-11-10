"""Moonshadow half-life comparison: python -m examples.moonshadow_decay [--half-life 1|2|3]."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import pickle
from time import perf_counter

from examples.sultai import LAND_NAMES, MANA_MODEL, SPELLS
from mana_lands import ManaSource as S
from mana_opportunities import CastingMode, Spell, SpellCost, spell_components
from mana_search import LocalManaEvaluator, ManaSpace, local_search

PROFILES = (*SPELLS[:2], Spell(3, SPELLS[2].modes), *SPELLS[3:7],
            SpellCost('UBG', 2), SpellCost('UBG', 1), SpellCost('2BG', 1),
            Spell(1, (CastingMode('1B'), CastingMode('3BB'))), SpellCost('B', 4))
NAMES = {**LAND_NAMES, S('UB', 'slow'): 'Shipwreck Marsh',
         S('BG', 'slow'): 'Deathcap Glade', S('UG', 'slow'): 'Dreamroot Cascade'}
SPELL_COUNTS = {'Superior Spider-Man': 4, 'Deceit': 4, 'Wistfulness': 4,
                'Formidable Speaker': 4, 'Bitter Triumph': 2, 'Emptiness': 3,
                'Sunderflock': 4, 'Awaken the Honored Dead': 2, 'Professor Dellian Fel': 1,
                "Glarb, Calamity's Augur": 1, 'Overlord of the Balemurk': 1, 'Moonshadow': 4}
INITIAL = {'Overgrown Tomb': 2, 'Watery Grave': 4, 'Breeding Pool': 4,
           'Swamp': 1, 'Island': 1, 'Cavern of Souls': 4, 'Starting Town': 4,
           'Gloomlake Verge': 3, 'Wastewood Verge': 2, 'Willowrush Verge': 1}
SHOCK, TOWN = .008, .015


def make_space():
    original = ManaSpace.from_colors(26, 'UBG', format='standard',
        families={'basic': (0, 2), 'shock': (0, 4), 'verge': (0, 4), 'fast': (0, 4)},
        fixed={S('WUBRG', 'cavern'): 4, S('WUBRG', 'town'): 4})
    return ManaSpace({**original.bounds, **{S(pair, 'slow'): (0, 4) for pair in ('UB', 'BG', 'UG')}}, 26)


def named(base):
    return {NAMES[s]: n for s, n in base.items() if n}


def run(h, shock_penalty=SHOCK):
    started = perf_counter()
    space = make_space()
    ev = LocalManaEvaluator(space, PROFILES, model=MANA_MODEL, half_life=h,
                            family_maximums={'basic': 2})
    assert spell_components(PROFILES)[0] == sum(SPELL_COUNTS.values()) == 34
    assert tuple(m.cost for m in PROFILES[6].modes) == ('7UU', '2UU', '1UU')
    cache_path = Path(f'.cache/moonshadow_decay_h{h}.pkl')
    if cache_path.exists():
        with cache_path.open('rb') as stream:
            signature, entries = pickle.load(stream)
        ev.restore_cache(signature, entries)
    starts = [('supplied', INITIAL),
              ('eight_shocks', json.loads(Path('reports/moonshadow_four_turn_penalty_sweep.json').read_text())['rows'][-1]['lands']),
              ('twelve_slowlands', json.loads(Path('reports/moonshadow_slow_search.json').read_text())['lands'])]
    if h == 1 and shock_penalty != SHOCK:
        starts.append(('previous_h1', json.loads(Path('reports/moonshadow_decay_h1.json').read_text())['lands']))
    report = {'half_life': h, 'horizon': ev.timing.horizon, 'tail_tolerance': .05,
              'omitted_mass': ev.timing.omitted_mass,
              'normalized_weights': [str(w) for w in ev.timing.weights],
              'shock_penalty': shock_penalty, 'town_penalty': TOWN,
              'position': 'both', 'opening_hand_size': 7, 'basic_cap': 2,
              'fixed': {'Cavern of Souls': 4, 'Starting Town': 4},
              'source_bounds': {NAMES[s]: list(b) for s, b in space.bounds.items()},
              'spell_profiles': [{'count': s.count, 'modes': [m.cost for m in s.modes]
                                 if isinstance(s, Spell) else [s.cost]} for s in PROFILES],
              'runs': [], 'baselines': {},
              'assumptions': ['Full original casting-mode shares; physical copies count once.',
                              'Uniform mode importance; no board state, sequencing or mulligans.',
                              'Cavern is unrestricted rainbow mana; slowlands explicitly added outside Standard filter.',
                              'Best found two-land local optimum; no global-optimum guarantee.',
                              'Tail threshold bounds omitted weight, not score or ranking error.']}
    winner = None
    for label, lands in starts:
        base = {s: lands.get(NAMES[s], 0) for s in space.sources}
        space.counts(base)
        baseline = ev.value(base, shock_penalty=shock_penalty, town_penalty=TOWN)
        report['baselines'][label] = {'score': float(baseline.score), 'raw': float(baseline.raw_score), 'lands': named(base)}
        budget, attempts = 2000, []
        while True:
            def progress(n, best):
                print(f'h={h} start={label} budget={budget} visits={n} score={float(best.score):.9f}', flush=True)
            result = local_search(ev, base, evaluation_budget=budget,
                                  shock_penalty=shock_penalty, town_penalty=TOWN, progress=progress)
            attempts.append({'budget': budget, 'visits': result.evaluations,
                             'seconds': result.seconds, 'stop': result.stopped})
            base = dict(zip(space.sources, result.best.counts))
            cache_path.parent.mkdir(exist_ok=True)
            with cache_path.open('wb') as stream:
                pickle.dump((ev.cache_signature, dict(ev.cache)), stream)
            if result.stopped == 'two-land local optimum':
                break
            budget *= 2
        if winner is None or result.best.score > winner.score:
            winner = result.best
        report['runs'].append({'start': label, 'attempts': attempts,
                               'score': float(result.best.score), 'lands': named(base)})
    base = dict(zip(space.sources, winner.counts))
    assert sum(base.values()) == 26
    assert sum(n for s, n in base.items() if s.kind == 'basic') <= 2
    assert all(space.bounds[s][0] <= n <= space.bounds[s][1] for s, n in base.items())
    initial = {s: INITIAL.get(NAMES[s], 0) for s in space.sources}
    # Every turn's contribution to the final normalized, discounted raw score.
    _, copies, weighted = spell_components(PROFILES)
    cost_weights = {cost: weighted[cost]/n for cost, n in copies.items()}
    contributions = {}
    for row in ev.components(base).opportunities:
        contributions[row.turn] = contributions.get(row.turn, Fraction()) + (
            row.expected_copies * cost_weights[row.cost] * ev.timing.weights[row.turn-1] / 2)
    report.update({'lands': named(base), 'score': float(winner.score), 'exact_score': str(winner.score),
                   'raw': float(winner.raw_score), 'penalty': float(winner.penalty),
                   'family_counts': {kind: sum(n for s, n in base.items() if s.kind == kind)
                                     for kind in ('shock', 'fast', 'slow', 'basic', 'verge')},
                   'out': {NAMES[s]: initial[s]-n for s, n in base.items() if initial[s] > n},
                   'in': {NAMES[s]: n-initial[s] for s, n in base.items() if n > initial[s]},
                   'weighted_contributions_by_turn': {t: float(v) for t, v in contributions.items()},
                   'unique_evaluations': len(ev.cache), 'seconds': perf_counter()-started})
    assert sum(contributions.values()) == winner.raw_score
    suffix = '' if shock_penalty == SHOCK else f'_shock{shock_penalty:g}'
    target = Path(f'reports/moonshadow_decay_h{h}{suffix}')
    target.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
    deck = 'Deck\n' + '\n'.join(f'{n} {name}' for name, n in {**SPELL_COUNTS, **named(base)}.items()) + '\n'
    target.with_suffix('.txt').write_text(deck)
    lines = [f'# Moonshadow: half-life {h}', '',
             f'Horizon: {ev.timing.horizon}; omitted weight: {ev.timing.omitted_mass:.4%}.',
             f'Score: {float(winner.score):.9f}; shocks {report["family_counts"]["shock"]}, '
             f'fast lands {report["family_counts"]["fast"]}, slowlands {report["family_counts"]["slow"]}.', '',
             f'Shock penalty: {shock_penalty:g}; Town penalty: {TOWN:g}. Full casting profiles.', '',
             '## Baselines under this weighting', '', '| Base | Score |', '| --- | ---: |']
    lines += [f'| {label} | {v["score"]:.9f} |' for label, v in report['baselines'].items()]
    lines += ['', '## Changes from supplied list', '', f'OUT: {report["out"]}', '', f'IN: {report["in"]}', '',
              '## Decklist', '', '```text', deck.rstrip(), '```', '', '## Assumptions', '']
    lines += [f'- {a}' for a in report['assumptions']]
    target.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k: report[k] for k in ('half_life', 'horizon', 'score', 'lands', 'seconds')}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--half-life', type=int, choices=(1, 2, 3))
    parser.add_argument('--shock-penalty', type=float, default=SHOCK)
    args = parser.parse_args()
    if not 0 <= args.shock_penalty < float('inf'):
        parser.error('--shock-penalty must be finite and nonnegative')
    for h in (args.half_life,) if args.half_life else (2, 3):
        run(h, shock_penalty=args.shock_penalty)


if __name__ == '__main__':
    main()
