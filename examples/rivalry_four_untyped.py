"""Latest Rivalry list with four untyped tapped duals, colors optimized."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import pickle
from time import perf_counter
from examples.vicious_rivalry_sweep import COUNTS as OLD_COUNTS, NAMES, SPELLS as OLD, make_space
from examples.sultai import MANA_MODEL
from mana_lands import ManaSource as S
from mana_opportunities import evaluate, spell_components
from mana_search import ManaSpace, LocalManaEvaluator, local_search

COUNTS = {**OLD_COUNTS, 'Sunderflock': 4, 'Awaken the Honored Dead': 2,
          'Overlord of the Balemurk': 2, 'Vicious Rivalry': 1}
SPELLS = tuple(replace(s, count={6:4, 7:2, 10:2, 11:1}.get(i,s.count)) for i,s in enumerate(OLD))
assert sum(COUNTS.values()) == spell_components(SPELLS)[0] == 34
CORE = {S('UB','shock','UB'):4, S('UG','shock','UG'):4,
        S('WUBRG','cavern'):4, S('WUBRG','town'):4, S('UB','verge'):2,
        S('BG','verge'):1, S('B','basic'):1, S('BG','slow'):2}
assert sum(CORE.values()) == 22

def run(h, budget=800, fixed_mix=None):
    started=perf_counter()
    original=make_space((0,8))
    mixes={'3bg1ub':{'UB':1,'BG':3,'UG':0},'4bg':{'UB':0,'BG':4,'UG':0}}
    fixed=mixes[fixed_mix] if fixed_mix else None
    space=ManaSpace({**original.bounds, **{S(p,'tapped'):((fixed[p],fixed[p]) if fixed else (0,4)) for p in ('UB','BG','UG')}},
                    26,{**original.family_bounds,'basic':(1,2),'tapped':(4,4)})
    ev=LocalManaEvaluator(space,SPELLS,model=MANA_MODEL,half_life=h)
    tag=str(float(h)).replace('.','_')
    suffix=f'_{fixed_mix}' if fixed_mix else ''
    stem=Path(f'reports/rivalry_four_untyped_h{tag}{suffix}')
    cache=Path(f'.cache/rivalry_four_untyped_h{tag}{suffix}.pkl')
    if cache.exists():
        with cache.open('rb') as f:sig,entries=pickle.load(f)
        ev.restore_cache(sig,entries)
    seeds=[]
    inverse={n:s for s,n in NAMES.items()}
    cores=[CORE]
    if fixed:
        previous=json.loads(Path(f'reports/rivalry_four_untyped_h{tag}.json').read_text())
        cores.append({inverse[n]:v for n,v in previous['lands'].items() if inverse[n].kind!='tapped'})
    for ub in range(5):
        for bg in range(5-ub):
            mix={'UB':ub,'BG':bg,'UG':4-ub-bg}
            if fixed and mix!=fixed:continue
            for core in cores:
                base={**core,**{S(p,'tapped'):n for p,n in mix.items()}}
                seeds.append((ev.value(base),base,mix))
    best,initial,mix=max(seeds,key=lambda row:row[0].score)
    report={'half_life':h,'max_replacements':1,'budget':budget,'spell_counts':COUNTS,
            'family_bounds':dict(space.family_bounds),
            'source_bounds':{NAMES[s]:list(b) for s,b in space.bounds.items()},
            'seed_mixes':[{'mix':m,'score':float(v.score)} for v,b,m in seeds],
            'selected_seed_mix':mix,'seed_score':float(best.score),
            'fixed_mix':fixed,'initial_lands':{NAMES[s]:n for s,n in initial.items() if n},
            'assumptions':['Four untyped tapped duals; no typed tapped duals offered.',
                           'No land abilities, life, sequencing or Cavern restrictions modeled.',
                           'One-swap local optimum only, not a global certificate.']}
    def checkpoint(n,best):
        lands={NAMES[s]:n for s,n in zip(space.sources,best.counts) if n}
        report.update(visits=n,score=float(best.score),exact_score=str(best.score),lands=lands,stop='running')
        stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
        stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{n} {k}' for k,n in {**COUNTS,**lands}.items())+'\n')
        print(f'h={h} visits={n} score={float(best.score):.12f} lands={lands}',flush=True)
    print(f'h={h} selected_seed={mix} score={float(best.score):.12f}',flush=True)
    result=local_search(ev,initial,evaluation_budget=budget,max_replacements=1,progress=checkpoint)
    base=dict(zip(space.sources,result.best.counts));space.counts(base)
    assert abs(evaluate(base,SPELLS,model=MANA_MODEL,half_life=h).score-float(result.best.score))<1e-12
    report.update(stop=result.stopped,search_seconds=result.seconds,elapsed_seconds=perf_counter()-started)
    stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    with cache.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--half-life',type=float,choices=(1.5,2),required=True)
    p.add_argument('--fixed-mix',choices=('3bg1ub','4bg'))
    args=p.parse_args();run(args.half_life,fixed_mix=args.fixed_mix)
