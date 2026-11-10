import json
from pathlib import Path
from examples.sultai import SPELLS, LAND_NAMES, MANA_MODEL
from mana_lands import ManaSource as S
from mana_opportunities import Spell, SpellCost, CastingMode, spell_components
from mana_search import ManaSpace, LocalManaEvaluator, local_search
spells=(*SPELLS[:2],Spell(3,SPELLS[2].modes),*SPELLS[3:7],SpellCost('BGU',2),SpellCost('BGU',1),SpellCost('2BG',1),Spell(1,tuple(CastingMode(c) for c in ('1B','3BB'))),SpellCost('B',4))
def mv(cost):
 return int(''.join(c for c in cost if c.isdigit()) or 0)+sum(c in 'WUBRG' for c in cost)
spells=tuple(Spell(s.count,tuple(m for m in s.modes if mv(m.cost)<=4),s.weight) if isinstance(s,Spell) else s for s in spells)
assert all(mv(m.cost)<=4 for s in spells if isinstance(s,Spell) for m in s.modes)
assert tuple(m.cost for m in spells[6].modes)==('2UU','1UU')
base={S('BG','shock','BG'):2,S('UB','shock','UB'):4,S('UG','shock','UG'):4,S('B','basic'):1,S('U','basic'):1,S('WUBRG','cavern'):4,S('WUBRG','town'):4,S('UB','verge'):3,S('BG','verge'):2,S('UG','verge'):1}
assert sum(base.values())==26 and spell_components(spells)[0]==34
report={'settings':{'shock_penalty':.012,'town_penalty':.015,'turns':4,'position':'both','fixed':'4 Cavern, 4 Town','basic_cap':2,'overlord_modes':['1B'],'moonshadow':'B'},'initial':{LAND_NAMES[s]:n for s,n in base.items()},'comparisons':{}}

LAND_NAMES.update({S('UB','slow'):'Shipwreck Marsh',S('BG','slow'):'Deathcap Glade',S('UG','slow'):'Dreamroot Cascade'})
original=ManaSpace.from_colors(26,'UBG',format='standard',families={'basic':(0,2),'shock':(0,4),'verge':(0,4),'fast':(0,4)},fixed={S('WUBRG','cavern'):4,S('WUBRG','town'):4})
space=ManaSpace({**original.bounds,**{S(pair,'slow'):(0,4) for pair in ('UB','BG','UG')}},26)
ev=LocalManaEvaluator(space,spells,model=MANA_MODEL,turns=4,family_maximums={'basic':2})
previous=dict(base)
previous[S('U','basic')]=0;previous[S('B','basic')]=2
previous[S('UG','shock','UG')]=3;previous[S('UG','verge')]=2
seed=dict(previous)
for pair in ('UB','BG','UG'):
 seed[S(pair,'shock',pair)]-=2;seed[S(pair,'slow')]=2
runs=[]
old_slow=json.loads(Path('reports/moonshadow_slow_search.json').read_text())['lands']
slow_start={s:old_slow.get(LAND_NAMES[s],0) for s in space.sources}
for start in (previous,seed,slow_start):
 r=local_search(ev,start,evaluation_budget=1500,shock_penalty=.012,town_penalty=.015,progress=lambda n,b:print(f'visits={n} score={float(b.score):.9f}',flush=True))
 runs.append(r)
 print('finished',r.stopped,flush=True)
winner=max((r.best for r in runs),key=lambda b:b.score)
report.update({'seven_turn_winner_rescored':float(ev.value(slow_start,shock_penalty=.012,town_penalty=.015).score),'spell_profiles':[{'count':s.count,'modes':[m.cost for m in s.modes] if isinstance(s,Spell) else [s.cost]} for s in spells],'previous_score':float(ev.value(previous,shock_penalty=.012,town_penalty=.015).score),'score':float(winner.score),'lands':{LAND_NAMES[s]:n for s,n in zip(space.sources,winner.counts) if n},'runs':[{'visits':r.evaluations,'stop':r.stopped,'score':float(r.best.score),'lands':{LAND_NAMES[s]:n for s,n in zip(space.sources,r.best.counts) if n}} for r in runs]})
Path('reports/moonshadow_four_turn_search.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
