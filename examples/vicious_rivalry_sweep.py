"""Vicious Rivalry sweep with 0-8 shocks and exactly two untyped tapped duals."""
import argparse,json,pickle
from pathlib import Path
from time import perf_counter
from examples.moonshadow_decay import NAMES,PROFILES as OLD,make_space
from mana_lands import ManaSource as S
from mana_opportunities import Spell,SpellCost,spell_components,evaluate
from mana_search import ManaSpace,LocalManaEvaluator,local_search

SPELLS=(*OLD[:6],Spell(3,OLD[6].modes),SpellCost('UBG',3),SpellCost('UBG',2),SpellCost('2BG',2),OLD[10],SpellCost('2BG',2))
COUNTS={'Superior Spider-Man':4,'Deceit':4,'Wistfulness':4,'Formidable Speaker':4,'Bitter Triumph':2,'Emptiness':3,'Sunderflock':3,'Awaken the Honored Dead':3,'Professor Dellian Fel':2,"Glarb, Calamity's Augur":2,'Overlord of the Balemurk':1,'Vicious Rivalry':2}
NAMES={**NAMES,**{S(pair,'tapped'):f'{pair} tapped dual' for pair in ('UB','BG','UG')}}
NAMES.update({S('UB','typed_tapped'):'Undercity Sewers',S('BG','typed_tapped'):'Underground Mortuary',S('UG','typed_tapped'):'Hedge Maze'})
BASE={S('BG','shock','BG'):2,S('UB','shock','UB'):4,S('UG','shock','UG'):3,S('B','basic'):2,S('WUBRG','cavern'):4,S('WUBRG','town'):4,S('UB','verge'):3,S('BG','verge'):3,S('UG','verge'):1}
assert sum(BASE.values())==26 and spell_components(SPELLS)[0]==sum(COUNTS.values())==34

def run(h, pairs=('UB','BG','UG'), suffix='', budget=500, max_replacements=2, save_cache=True, typed_tapped=False, min_basics=0):
 started=perf_counter()
 original=make_space((0,8))
 tapped_kind='typed_tapped' if typed_tapped else 'tapped'
 space=ManaSpace({**original.bounds,**{S(pair,tapped_kind):(0,2) for pair in ('UB','BG','UG')}},26,{**original.family_bounds,'basic':(min_basics,2),tapped_kind:(2,2)})
 variant=f'_typed_basic{min_basics}' if typed_tapped or min_basics else ''
 suffix=variant+suffix
 from examples.sultai import MANA_MODEL
 ev=LocalManaEvaluator(space,SPELLS,model=MANA_MODEL,half_life=h)
 tag=str(h).replace('.','_');cache=Path(f'.cache/rivalry_h{tag}{suffix}.pkl')
 cache.parent.mkdir(exist_ok=True)
 restore=cache if cache.exists() or variant else Path(f'.cache/rivalry_h{tag}.pkl')
 if restore.exists():
  with restore.open('rb') as f:sig,entries=pickle.load(f)
  ev.restore_cache(sig,entries)
 loaded=perf_counter(); initial_cache_entries=len(ev.cache)
 runs=[];winner=None
 for pair in pairs:
  base=dict(BASE);base[S(pair,'shock',pair)]-=2;base[S(pair,tapped_kind)]=2
  before=len(ev.cache)
  result=local_search(ev,base,evaluation_budget=budget,max_replacements=max_replacements,progress=lambda n,b:print(f'h={h} start={pair} visits={n} score={float(b.score):.12f}',flush=True))
  attempts=[{'budget':budget,'visits':result.evaluations,'seconds':result.seconds,'stop':result.stopped}]
  runs.append({'start':pair,'score':float(result.best.score),'new_evaluations':len(ev.cache)-before,'attempts':attempts,'lands':{NAMES[s]:n for s,n in zip(space.sources,result.best.counts) if n}})
  if winner is None or result.best.score>winner.score:winner=result.best
  if save_cache:
   with cache.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
 base=dict(zip(space.sources,winner.counts));space.counts(base)
 assert sum(n for s,n in base.items() if s.kind==tapped_kind)==2
 assert min_basics<=sum(n for s,n in base.items() if s.kind=='basic')<=2
 assert sum(n for s,n in base.items() if s.kind=='shock')<=8
 assert abs(evaluate(base,SPELLS,model=MANA_MODEL,half_life=h).score-float(winner.score))<1e-12
 lands={NAMES[s]:n for s,n in base.items() if n}
 report={'schema_version':2,'spell_counts':COUNTS,'half_life':h,'horizon':ev.timing.horizon,'omitted_mass':ev.timing.omitted_mass,'score':float(winner.score),'exact_score':str(winner.score),'lands':lands,'family_bounds':dict(space.family_bounds),'runs':runs,'assumptions':['Tapped slots are untyped duals, not typed surveil lands.','Full casting profiles, uniform mode shares.','Cavern unrestricted; life, sequencing and land abilities not simulated.','Best-found two-land local optimum, not global certification.']}
 report.update({'source_bounds':{NAMES[s]:list(b) for s,b in space.bounds.items()},'normalized_weights':[str(w) for w in ev.timing.weights],'spell_profiles':[{'count':s.count,'modes':[{'cost':m.cost,'weight':m.weight} for m in s.modes] if isinstance(s,Spell) else [{'cost':s.cost,'weight':1}]} for s in SPELLS],'family_counts':{kind:sum(n for s,n in base.items() if s.kind==kind) for kind in sorted({s.kind for s in space.sources})},'card_text_source':'https://www.mtg.wtf/card/sos/241/Vicious-Rivalry'})
 report['assumptions'][-1]='Best found within a fixed evaluation budget; see per-start completion status.'
 if typed_tapped:report['assumptions'][0]='Exactly two typed tapped duals; surveil is not modeled.'
 report.update(max_replacements=max_replacements,evaluation_budget_per_start=budget,initial_cache_entries=initial_cache_entries,cache_load_seconds=loaded-started,search_seconds=sum(a['seconds'] for r in runs for a in r['attempts']),elapsed_seconds=perf_counter()-started)
 stem=Path(f'reports/vicious_rivalry_h{tag}{suffix}')
 stem.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
 stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{n} {name}' for name,n in {**COUNTS,**lands}.items())+'\n')
 print(json.dumps({k:report[k] for k in ('half_life','score','lands','runs','cache_load_seconds','search_seconds','elapsed_seconds')}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--half-life',type=float,required=True);p.add_argument('--start',choices=('UB','BG','UG'));p.add_argument('--budget',type=int,default=500);p.add_argument('--max-replacements',type=int,choices=(1,2),default=2);p.add_argument('--no-save-cache',action='store_true');p.add_argument('--typed-tapped',action='store_true');p.add_argument('--min-basics',type=int,choices=(0,1,2),default=0)
 args=p.parse_args();suffix=(f'_{args.start}' if args.start else '')+('_one_swap' if args.max_replacements==1 else '')
 run(args.half_life,(args.start,) if args.start else ('UB','BG','UG'),suffix,args.budget,args.max_replacements,not args.no_save_cache,args.typed_tapped,args.min_basics)
