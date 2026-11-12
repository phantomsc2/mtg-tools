"""Large-budget h=2 multistart comparison of six fixed typed-dual pairs."""
import argparse
from itertools import combinations_with_replacement
import json
import pickle
from pathlib import Path
import random
from time import perf_counter
from examples.rivalry_four_untyped import COUNTS, SPELLS, CORE, NAMES
from examples.sultai import MANA_MODEL
from mtg_tools.mana_lands import ManaSource as S
from mtg_tools.mana_search import ManaSpace, LocalManaEvaluator, local_search
from mtg_tools.mana_opportunities import evaluate

PAIRS=list(combinations_with_replacement(('UB','BG','UG'),2))

def run(case):
    started=perf_counter(); pair=PAIRS[case-1]
    fixed={S('WUBRG','cavern'):4,S('WUBRG','town'):4,S('BG','tapped'):2}
    fixed.update({S(p,'typed_tapped'):pair.count(p) for p in ('UB','BG','UG')})
    space=ManaSpace.from_colors(26,'UBG',families={'basic':(0,26),'shock':(0,4),
                       'fast':(0,4),'slow':(0,4),'verge':(0,4)},fixed=fixed,
                       family_bounds={'basic':(1,26),'shock':(0,8)})
    names={**NAMES,S('UB','fast'):'Darkslick Shores',S('BG','tapped'):'Restless Cottage'}
    ev=LocalManaEvaluator(space,SPELLS,model=MANA_MODEL,half_life=2)
    stem=Path(f'ideas/reports/rivalry_cottage_h2_case{case}_shock8');cache=Path(f'.cache/rivalry_cottage_h2_case{case}_shock8.pkl')
    recovered=0
    if cache.exists():
        with cache.open('rb') as f:sig,entries=pickle.load(f)
        ev.restore_cache(sig,entries)
    else:
        old_cache=Path(f'.cache/rivalry_cottage_h2_case{case}.pkl')
        if old_cache.exists():
            with old_cache.open('rb') as f:sig,entries=pickle.load(f)
            # Only aggregate bounds changed. Scores depend on the physical base,
            # model, spells and timing, not on search-space aggregate limits.
            assert sig[:-1]==ev.cache_signature[:-1]
            assert dict(sig[-1])=={'basic':(1,26)}
            eligible={}
            for counts,value in entries.items():
                try:space.counts(dict(zip(space.sources,counts)))
                except ValueError:continue
                eligible[counts]=value
            ev.restore_cache(ev.cache_signature,eligible);recovered=len(eligible)
            old_report=Path(f'ideas/reports/rivalry_cottage_h2_case{case}.json')
            if old_report.exists():
                previous=json.loads(old_report.read_text())
                previous['stop']='superseded_by_shock8_restart'
                old_report.write_text(json.dumps(previous,indent=2)+'\n')
    supplied={**CORE,**fixed}
    rich={**fixed,S('U','basic'):1,S('UB','shock','UB'):4,S('UG','shock','UG'):4,
          S('UB','verge'):3,S('BG','verge'):2}
    starts=[('supplied',supplied),('shock8_verges',rich)]
    rng=random.Random(20261111+case)
    flexible=[s for s in space.sources if s not in fixed]
    for i in range(2):
        base=dict(fixed);base[rng.choice([S(c,'basic') for c in 'UBG'])]=1
        while sum(base.values())<26:
            s=rng.choice(flexible)
            if s.kind=='shock' and sum(n for land,n in base.items() if land.kind=='shock')>=8:continue
            if base.get(s,0)<space.bounds[s][1]:base[s]=base.get(s,0)+1
        starts.append((f'random_{i+1}',base))
    report={'case':case,'typed_pair':pair,'half_life':2,'spell_counts':COUNTS,
            'max_replacements':1,'budget_per_start':2500,'random_seed':20261111+case,
            'source_bounds':{names[s]:list(b) for s,b in space.bounds.items()},
            'family_bounds':dict(space.family_bounds),'runs':[],'recovered_evaluations':recovered,
            'assumptions':['Exactly two Restless Cottages and the specified two typed duals.',
              'At most eight shocks; no basic maximum; all three Sultai fastlands offered.',
              'Land abilities, life, sequencing and Cavern restrictions not modeled.',
              'One-swap multistart search, not global certification.']}
    winner=None
    for label,base in starts:
        space.counts(base)
        def checkpoint(n,best):
            nonlocal winner
            if winner is None or best.score>winner.score:winner=best
            report.update(score=float(winner.score),exact_score=str(winner.score),
                  lands={names[s]:v for s,v in zip(space.sources,winner.counts) if v},
                  active_start=label,active_visits=n,stop='running',elapsed_seconds=perf_counter()-started)
            stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
            stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{v} {k}' for k,v in {**COUNTS,**report['lands']}.items())+'\n')
            print(f'case={case} start={label} visits={n} best={float(best.score):.12f} overall={float(winner.score):.12f}',flush=True)
        result=local_search(ev,base,evaluation_budget=2500,max_replacements=1,progress=checkpoint)
        report['runs'].append({'start':label,'initial_lands':{names[s]:v for s,v in base.items() if v},
                'score':float(result.best.score),'lands':{names[s]:v for s,v in zip(space.sources,result.best.counts) if v},
                'visits':result.evaluations,'seconds':result.seconds,'stop':result.stopped})
        report['stop']='between starts'
        stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
        with cache.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
    bestbase=dict(zip(space.sources,winner.counts));space.counts(bestbase)
    assert abs(evaluate(bestbase,SPELLS,model=MANA_MODEL,half_life=2).score-float(winner.score))<1e-12
    report.update(stop='complete',elapsed_seconds=perf_counter()-started,unique_evaluations=len(ev.cache))
    stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'case':case,'score':report['score'],'lands':report['lands'],'runs':report['runs']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=int,choices=range(1,7),required=True)
    run(p.parse_args().case)
