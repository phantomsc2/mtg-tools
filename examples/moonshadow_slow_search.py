import json
from pathlib import Path
from examples.sultai import SPELLS, LAND_NAMES, MANA_MODEL
from mana_lands import ManaSource as S
from mana_opportunities import Spell, SpellCost, CastingMode, spell_components
from mana_search import ManaSpace, LocalManaEvaluator, local_search
spells=(*SPELLS[:2],Spell(3,SPELLS[2].modes),*SPELLS[3:7],SpellCost('BGU',2),SpellCost('BGU',1),SpellCost('2BG',1),Spell(1,tuple(CastingMode(c) for c in ('1B','3BB'))),SpellCost('B',4))
base={S('BG','shock','BG'):2,S('UB','shock','UB'):4,S('UG','shock','UG'):4,S('B','basic'):1,S('U','basic'):1,S('WUBRG','cavern'):4,S('WUBRG','town'):4,S('UB','verge'):3,S('BG','verge'):2,S('UG','verge'):1}
assert sum(base.values())==26 and spell_components(spells)[0]==34
report={'settings':{'shock_penalty':.012,'town_penalty':.015,'turns':7,'position':'both','fixed':'4 Cavern, 4 Town','basic_cap':2,'overlord_modes':['1B','3BB'],'moonshadow':'B'},'initial':{LAND_NAMES[s]:n for s,n in base.items()},'comparisons':{}}

LAND_NAMES.update({S('UB','slow'):'Shipwreck Marsh',S('BG','slow'):'Deathcap Glade',S('UG','slow'):'Dreamroot Cascade'})
original=ManaSpace.from_colors(26,'UBG',format='standard',families={'basic':(0,2),'shock':(0,4),'verge':(0,4),'fast':(0,4)},fixed={S('WUBRG','cavern'):4,S('WUBRG','town'):4})
space=ManaSpace({**original.bounds,**{S(pair,'slow'):(0,4) for pair in ('UB','BG','UG')}},26)
ev=LocalManaEvaluator(space,spells,model=MANA_MODEL,family_maximums={'basic':2})
previous=dict(base)
previous[S('U','basic')]=0;previous[S('B','basic')]=2
previous[S('UG','shock','UG')]=3;previous[S('UG','verge')]=2
seed=dict(previous)
for pair in ('UB','BG','UG'):
 seed[S(pair,'shock',pair)]-=2;seed[S(pair,'slow')]=2
runs=[]
for start in (previous,seed):
 r=local_search(ev,start,evaluation_budget=1500,shock_penalty=.012,town_penalty=.015,progress=lambda n,b:print(f'visits={n} score={float(b.score):.9f}',flush=True))
 runs.append(r)
 print('finished',r.stopped,flush=True)
winner=max((r.best for r in runs),key=lambda b:b.score)
report.update({'previous_score':float(ev.value(previous,shock_penalty=.012,town_penalty=.015).score),'score':float(winner.score),'lands':{LAND_NAMES[s]:n for s,n in zip(space.sources,winner.counts) if n},'runs':[{'visits':r.evaluations,'stop':r.stopped,'score':float(r.best.score),'lands':{LAND_NAMES[s]:n for s,n in zip(space.sources,r.best.counts) if n}} for r in runs]})
Path('reports/moonshadow_slow_search.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
