"""Full-profile Moonshadow searches with raw scores and explicit space limits."""
import argparse
from fractions import Fraction
import json
from math import fsum
from pathlib import Path
import pickle
from time import perf_counter

from examples.sultai import LAND_NAMES, MANA_MODEL, SPELLS
from mtg_tools.mana_lands import ManaSource as S
from mtg_tools.mana_opportunities import CastingMode, Spell, SpellCost, spell_components
from mtg_tools.mana_search import LocalManaEvaluator, ManaSpace, local_search

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


def make_space(shocks=(0, 12)):
    original = ManaSpace.from_colors(26, 'UBG', format='standard',
        families={'basic': (0, 2), 'shock': (0, 4), 'verge': (0, 4), 'fast': (0, 4)},
        fixed={S('WUBRG', 'cavern'): 4, S('WUBRG', 'town'): 4})
    return ManaSpace({**original.bounds, **{S(pair, 'slow'): (0, 4) for pair in ('UB', 'BG', 'UG')}}, 26,
                     family_bounds={'basic': (0, 2), 'shock': shocks, 'town': (4, 4)})


def named(base):
    return {NAMES[s]: n for s, n in base.items() if n}


def complete_search(evaluator, base, progress=None, budget=2000):
    attempts = []
    while True:
        result = local_search(evaluator, base, evaluation_budget=budget, progress=progress)
        attempts.append({'budget': budget, 'visits': result.evaluations,
                         'seconds': result.seconds, 'stop': result.stopped})
        if result.stopped == 'two-land local optimum':
            return result, attempts
        base = dict(zip(evaluator.space.sources, result.best.counts))
        budget *= 2


def write_deck(path, lands):
    assert sum(lands.values()) == 26 and sum(SPELL_COUNTS.values()) == 34
    Path(path).write_text('Deck\n'+'\n'.join(f'{n} {name}' for name,n in {**SPELL_COUNTS,**lands}.items())+'\n')


def run(h):
    started = perf_counter()
    space = make_space()
    ev = LocalManaEvaluator(space, PROFILES, model=MANA_MODEL, half_life=h)
    cache_path = Path(f'.cache/raw_moonshadow_h{h}.pkl')
    if cache_path.exists():
        with cache_path.open('rb') as f: signature, entries = pickle.load(f)
        ev.restore_cache(signature, entries)
    eight = {'Cavern of Souls':4,'Starting Town':4,'Overgrown Tomb':4,'Watery Grave':4,
             'Deathcap Glade':1,'Shipwreck Marsh':4,'Dreamroot Cascade':3,'Willowrush Verge':2}
    twelve = {'Cavern of Souls':4,'Starting Town':4,'Overgrown Tomb':4,'Watery Grave':4,
              'Breeding Pool':4,'Shipwreck Marsh':2,'Wastewood Verge':1,'Gloomlake Verge':3}
    starts = [('supplied',INITIAL),('eight_shocks',eight),('twelve_shocks',twelve)]
    # Starting from the strongest previously evaluated base avoids losing cached discoveries.
    if ev.cache:
        strongest = max(ev.cache, key=lambda c: ev.value(dict(zip(space.sources,c))).score)
        starts.append(('strongest_cached',named(dict(zip(space.sources,strongest)))))
    report = {'schema_version':2,'half_life':h,'horizon':ev.timing.horizon,'omitted_mass':ev.timing.omitted_mass,
              'tail_tolerance':.05,'normalized_weights':[str(w) for w in ev.timing.weights],
              'family_bounds':dict(space.family_bounds),'source_bounds':{NAMES[s]:list(b) for s,b in space.bounds.items()},
              'spell_profiles':[{'count':s.count,'modes':[m.cost for m in s.modes] if isinstance(s,Spell) else [s.cost]} for s in PROFILES],
              'runs':[],'baselines':{},'assumptions':['Full original casting profiles; uniform mode shares.',
              'No sequencing, mulligans or life totals; Cavern is unrestricted rainbow mana.',
              'Sultai slowlands are explicitly added outside the Standard snapshot.',
              'Best found two-land local optimum; no global-optimum guarantee.']}
    winner = None
    for label,lands in starts:
        base={s:lands.get(NAMES[s],0) for s in space.sources}
        report['baselines'][label]={'score':float(ev.value(base).score),'lands':named(base)}
        result,attempts=complete_search(ev,base,progress=lambda n,b:print(f'h={h} {label} visits={n} score={float(b.score):.9f}',flush=True))
        base=dict(zip(space.sources,result.best.counts))
        report['runs'].append({'start':label,'attempts':attempts,'score':float(result.best.score),'lands':named(base)})
        if winner is None or result.best.score>winner.score:winner=result.best
        cache_path.parent.mkdir(exist_ok=True)
        with cache_path.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
    base=dict(zip(space.sources,winner.counts))
    report.update({'score':float(winner.score),'exact_score':str(winner.score),'lands':named(base),
                   'family_counts':{kind:sum(n for s,n in base.items() if s.kind==kind) for kind in ('shock','slow','fast','basic','verge')},
                   'seconds':perf_counter()-started,'unique_evaluations':len(ev.cache)})
    path=Path(f'ideas/reports/moonshadow_decay_h{h}')
    path.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    write_deck(path.with_suffix('.txt'), report['lands'])
    lines=[f'# Moonshadow half-life {h}: raw-score optimization','',
           f'Horizon {ev.timing.horizon}; omitted weight {ev.timing.omitted_mass:.4%}.',
           f'Score: {float(winner.score):.12f}. Explicit family bounds: {dict(space.family_bounds)}.', '',
           '| Land | Count |','| --- | ---: |']
    lines += [f'| {name} | {n} |' for name,n in report['lands'].items()]
    lines += ['', '## Baselines under this weighting','', '| Base | Score |','| --- | ---: |']
    lines += [f'| {label} | {r["score"]:.12f} |' for label,r in report['baselines'].items()]
    lines += ['', '## Assumptions','']+[f'- {a}' for a in report['assumptions']]
    path.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:report[k] for k in ('half_life','score','lands')}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--half-life',type=int,choices=(1,2,3))
    args=parser.parse_args()
    for h in (args.half_life,) if args.half_life else (2,3):run(h)

if __name__=='__main__':main()
