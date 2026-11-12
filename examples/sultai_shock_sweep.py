"""Compare raw opportunities with exactly eight, nine and ten shocks."""
import json
from pathlib import Path
from time import perf_counter

from examples.sultai import LAND_NAMES, MANA_BASE, MANA_MODEL, SPELLS
from examples.sultai_optimize import make_space
from mtg_tools.mana.evaluation import LocalManaEvaluator
from mtg_tools.mana.space import ManaSpace
from mtg_tools.mana.local import local_search


def render(report):
    rows=report['results']
    lines=['# Sultai raw-score comparison: 8-10 shocks','',
           'Each shock count is an explicit search-space constraint. Scores measure casting opportunities.',
           'Four Caverns, four Towns and two Cottages are fixed; basics total at most two; Palace at most two.', '',
           '| Land | 8 shocks | 9 shocks | 10 shocks |','| --- | ---: | ---: | ---: |']
    for name in sorted({name for r in rows for name in r['lands']}):
        lines.append('| '+name+' | '+' | '.join(str(r['lands'].get(name,0)) for r in rows)+' |')
    lines += ['', '| Shocks | Score | Stop |','| ---: | ---: | --- |']
    lines += [f'| {r["shocks"]} | {r["score"]:.12f} | {r["stopped"]} |' for r in rows]
    lines += ['', 'A budget stop is not a local-optimum certificate. A complete run checks two-land replacements.',
              'No sequencing, life totals, or Cavern restrictions are simulated.',
              f'Total runtime: {report["seconds"]:.2f}s; budget {report["budget"]} visits per count.']
    return '\n'.join(lines)+'\n'


def main():
    space=make_space()
    projector=LocalManaEvaluator(space,SPELLS,model=MANA_MODEL)
    current=dict(MANA_BASE)
    rows=[]
    started=perf_counter()
    budget=500
    for total in range(8,11):
        while sum(n for s,n in current.items() if s.kind=='shock') != total:
            existing=sum(n for s,n in current.items() if s.kind=='shock')
            wanted=existing+(1 if existing<total else -1)
            candidates=[projector.value(dict(zip(space.sources,c))) for c in projector.space.neighbor_counts(current)
                        if sum(n for s,n in zip(space.sources,c) if s.kind=='shock')==wanted]
            seed=max(candidates,key=lambda r:r.score)
            current=dict(zip(space.sources,seed.counts))
        limited=ManaSpace(space.bounds,space.land_count,{**space.family_bounds,'shock':(total,total)})
        ev=LocalManaEvaluator(limited,SPELLS,model=MANA_MODEL)
        result=local_search(ev,current,evaluation_budget=budget,
                            progress=lambda n,r:print(f'{total} shocks: {n} visits score={float(r.score):.9f}',flush=True))
        current=dict(zip(space.sources,result.best.counts))
        rows.append({'shocks':total,'score':float(result.best.score),'exact_score':str(result.best.score),
                     'lands':{LAND_NAMES[s]:n for s,n in current.items() if n},
                     'family_bounds':dict(limited.family_bounds),'evaluations':result.evaluations,
                     'stopped':result.stopped,'seconds':result.seconds})
    report={'schema_version':2,'budget':budget,'seconds':perf_counter()-started,'results':rows}
    Path('ideas/reports/sultai_shock_sweep.json').write_text(json.dumps(report,indent=2)+'\n')
    Path('ideas/reports/sultai_shock_sweep.md').write_text(render(report))

if __name__=='__main__':main()
