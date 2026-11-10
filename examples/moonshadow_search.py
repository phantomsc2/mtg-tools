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
for fast in (False,True):
 families={'basic':(0,2),'shock':(0,4),'verge':(0,4)}
 if fast: families['fast']=(0,4)
 space=ManaSpace.from_colors(26,'UBG',format='standard',families=families,fixed={S('WUBRG','cavern'):4,S('WUBRG','town'):4})
 ev=LocalManaEvaluator(space,spells,model=MANA_MODEL,family_maximums={'basic':2})
 starts=[base]
 if fast:
  seed=dict(base)
  for pair,n in [('UG',4),('BG',1)]:
   seed[S(pair,'shock',pair)]-=n;seed[S(pair,'fast')]=n
  starts.append(seed)
 runs=[]
 for start in starts:
  r=local_search(ev,start,evaluation_budget=1500,shock_penalty=.012,town_penalty=.015,progress=lambda n,b:print(f'fast={fast} visits={n} score={float(b.score):.9f}',flush=True))
  runs.append(r)
 winner=max((r.best for r in runs),key=lambda b:b.score)
 baseline=ev.value(base,shock_penalty=.012,town_penalty=.015)
 result={'score':float(winner.score),'raw':float(winner.raw_score),'baseline_score':float(baseline.score),'delta':float(winner.score-baseline.score),'lands':{LAND_NAMES[s]:n for s,n in zip(space.sources,winner.counts) if n},'runs':[{'visits':r.evaluations,'stop':r.stopped,'seconds':r.seconds} for r in runs]}
 report['comparisons']['fast' if fast else 'no_fast']=result
 Path('reports/moonshadow_search.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(result),flush=True)


