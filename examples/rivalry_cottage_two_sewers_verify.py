"""Two-land search around the best completed h=2 two-Sewers base."""
import json
import pickle
from pathlib import Path
from time import perf_counter
from examples.rivalry_cottage_sweep import COUNTS, SPELLS, NAMES
from examples.sultai import MANA_MODEL
from mtg_tools.mana_lands import ManaSource as S
from mtg_tools.mana_opportunities import evaluate
from mtg_tools.mana_search import ManaSpace, LocalManaEvaluator, local_search


def main():
    started=perf_counter()
    fixed={S('WUBRG','cavern'):4,S('WUBRG','town'):4,S('BG','tapped'):2,
           S('UB','typed_tapped'):2,S('BG','typed_tapped'):0,S('UG','typed_tapped'):0}
    space=ManaSpace.from_colors(26,'UBG',families={'basic':(0,26),'shock':(0,4),
             'fast':(0,4),'slow':(0,4),'verge':(0,4)},fixed=fixed,
             family_bounds={'basic':(1,26),'shock':(0,8)})
    names={**NAMES,S('UB','fast'):'Darkslick Shores',S('BG','tapped'):'Restless Cottage'}
    ev=LocalManaEvaluator(space,SPELLS,model=MANA_MODEL,half_life=2)
    for path in (Path('.cache/rivalry_cottage_h2_case1_shock8.pkl'),Path('.cache/rivalry_cottage_h2_case1_two_swap.pkl')):
        if path.exists():
            with path.open('rb') as f:sig,entries=pickle.load(f)
            ev.restore_cache(sig,entries)
    seed=json.loads(Path('ideas/reports/rivalry_cottage_h2_case1_shock8.json').read_text())
    inverse={names[s]:s for s in space.sources}
    initial={inverse[k]:n for k,n in seed['lands'].items()}
    neighbors=ev.neighbor_counts(initial,max_replacements=2)
    report={'half_life':2,'budget':5000,'max_replacements':2,'baseline_score':seed['score'],
            'baseline_lands':seed['lands'],'initial_neighbors':len(neighbors),
            'initial_uncached':sum(c not in ev.cache for c in neighbors),
            'family_bounds':dict(space.family_bounds),'spell_counts':COUNTS,
            'assumptions':['One- and two-swap local search; no global certificate.',
                           'Cavern unrestricted; life, sequencing, surveil and manland abilities not modeled.']}
    stem=Path('ideas/reports/rivalry_cottage_h2_two_sewers_two_swap')
    best_seen=None
    original_value=ev.value
    def score(base):
        nonlocal best_seen
        result=original_value(base)
        if best_seen is None or result.score>best_seen.score:
            best_seen=result
            lands={names[s]:n for s,n in zip(space.sources,result.counts) if n}
            report.update(score=float(result.score),exact_score=str(result.score),lands=lands,
                          stop='running',elapsed_seconds=perf_counter()-started)
            stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
            stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{n} {name}' for name,n in {**COUNTS,**lands}.items())+'\n')
            print(f'improvement score={float(result.score):.12f} lands={lands}',flush=True)
        return result
    ev.value=score
    print(f"initial_neighbors={len(neighbors)} uncached={report['initial_uncached']}",flush=True)
    result=local_search(ev,initial,evaluation_budget=5000,max_replacements=2,
                        progress=lambda n,b:print(f'visits={n} score={float(b.score):.12f}',flush=True))
    base=dict(zip(space.sources,result.best.counts));space.counts(base)
    assert abs(evaluate(base,SPELLS,model=MANA_MODEL,half_life=2).score-float(result.best.score))<1e-12
    report.update(stop=result.stopped,visits=result.evaluations,seconds=result.seconds,
                  moves=[{'score':float(m.score),'removed':{names[s]:n for s,n in m.swap.out},
                          'added':{names[s]:n for s,n in m.swap.incoming}} for m in result.moves])
    stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    with Path('.cache/rivalry_cottage_h2_case1_two_swap.pkl').open('wb') as f:
        pickle.dump((ev.cache_signature,dict(ev.cache)),f)
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()
