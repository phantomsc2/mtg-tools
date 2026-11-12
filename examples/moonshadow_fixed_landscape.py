"""Direct raw-score comparison of fixed shock counts for the Moonshadow deck."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import pickle

from examples.moonshadow_decay import (PROFILES, NAMES, MANA_MODEL, make_space, named,
                                      complete_search, write_deck)
from mtg_tools.mana_search import LocalManaEvaluator, ManaSpace


def neighbors(space, counts, shocks, *, radius=2, basic_cap=2):
    constrained = ManaSpace(space.bounds, space.land_count,
                           {**space.family_bounds, 'shock': (shocks, shocks), 'basic': (0, basic_cap)})
    ev = LocalManaEvaluator(constrained, (), model=MANA_MODEL, turns=1)
    return ev.neighbor_counts(dict(zip(space.sources, counts)), max_replacements=radius)


def write_report(results):
    for k,result in sorted(results.items()):
        result['marginal_gain'] = None if k==8 else float(Fraction(result['exact_score'])-Fraction(results[k-1]['exact_score']))
    report={'schema_version':2,'settings':{'half_life':2,'horizon':9,'full_profiles':True,
            'family_bounds':{'shock':[8,12],'town':[4,4],'basic':[0,2]}},'results':results,
            'limitation':'Best-found fixed-count raw results, not a global optimum certificate.'}
    Path('ideas/reports/moonshadow_h2_landscape.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# h=2 fixed-shock raw-score comparison','',report['limitation'],'',
           '| Shocks | Score | Marginal gain |','| ---: | ---: | ---: |']
    for k,r in sorted(results.items()):
        gain='-' if r['marginal_gain'] is None else f'{r["marginal_gain"]:.12f}'
        lines.append(f'| {k} | {r["score"]:.12f} | {gain} |')
    lines += ['', '## Land counts','', '| Land | 8 | 9 | 10 | 11 | 12 |',
              '| --- | ---: | ---: | ---: | ---: | ---: |']
    for name in sorted(set().union(*(r['lands'] for r in results.values()))):
        lines.append('| '+name+' | '+' | '.join(str(results[k]['lands'].get(name,0)) for k in sorted(results))+' |')
    lines += ['', '## Method and provenance','',
              'Shock count is enforced directly by ManaSpace.family_bounds. Each count is optimized independently.',
              'Four Caverns and four Towns are fixed; at most two basics. Full casting profiles, half-life two, horizon nine.',
              'Raw scores are directly comparable across these counts. They measure mana opportunities, not life loss or win rate.']
    for k,r in sorted(results.items()):
        lines += ['', f'### {k} shocks', '', r.get('provenance','Staged one-land descent and two-land completion checks from three diverse cached starts.'),
                  f'[Full decklist](moonshadow_h2_fixed_{k}shocks.txt)']
    Path('ideas/reports/moonshadow_h2_landscape.md').write_text('\n'.join(lines)+'\n')


def run(k):
    space=make_space((k,k))
    ev=LocalManaEvaluator(space,PROFILES,model=MANA_MODEL,half_life=2)
    cache_path=Path(f'.cache/raw_moonshadow_h2_shock{k}.pkl')
    if cache_path.exists():
        with cache_path.open('rb') as f:sig,entries=pickle.load(f)
        ev.restore_cache(sig,entries)
    if not ev.cache:
        # A retained fixed-count base is a valid seed, never an imposed winner.
        part=Path(f'ideas/reports/moonshadow_h2_landscape_part_{k}.json')
        if part.exists():
            lands=json.loads(part.read_text())['lands']
            seed={s:lands.get(NAMES[s],0) for s in space.sources}
            ev.value(seed)
            for c in ev.neighbor_counts(seed):ev.value(dict(zip(space.sources,c)))
        else:
            c=next(space.exhaustive())
            ev.value(dict(zip(space.sources,c)))
    pool=sorted(ev.cache,key=lambda c:(-ev.value(dict(zip(space.sources,c))).score,c))[:250]
    seeds=[pool[0]]
    while len(seeds)<3:
        choices=[c for c in pool if c not in seeds]
        if not choices:break
        seeds.append(max(choices,key=lambda c:min(sum(abs(a-b) for a,b in zip(c,s)) for s in seeds)))
    runs=[]
    for i,c in enumerate(seeds):
        result,attempts=complete_search(ev,dict(zip(space.sources,c)),
              progress=lambda n,b:print(f'{k} shocks start {i+1}: {n} score={float(b.score):.12f}',flush=True))
        runs.append({'score':float(result.best.score),'exact_score':str(result.best.score),
                     'lands':named(dict(zip(space.sources,result.best.counts))),'attempts':attempts})
        with cache_path.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
    winner=max(runs,key=lambda r:Fraction(r['exact_score']))
    result={**winner,'runs':runs,'family_bounds':dict(space.family_bounds),
            'stop':'two-land local optimum','provenance':'Reoptimized with the staged library search and raw scoring.'}
    Path(f'ideas/reports/moonshadow_h2_landscape_part_{k}.json').write_text(json.dumps(result,indent=2)+'\n')
    write_deck(f'ideas/reports/moonshadow_h2_fixed_{k}shocks.txt',result['lands'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count',type=int,choices=range(8,13))
    parser.add_argument('--merge',action='store_true')
    args=parser.parse_args()
    if not args.merge:
        for k in (args.count,) if args.count is not None else range(8,13):run(k)
    if args.count is None or args.merge:
        write_report({k:json.loads(Path(f'ideas/reports/moonshadow_h2_landscape_part_{k}.json').read_text()) for k in range(8,13)})

if __name__=='__main__':main()
