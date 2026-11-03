import importlib.util,json,pickle
from pathlib import Path
from fractions import Fraction as F
from math import comb,lcm
from time import perf_counter
from unittest.mock import patch
import numpy as np
import mana_batch as batch
from mana_search import ManaSpace,ComponentTable,build_component_table
from mana_opportunities import Spell,SpellCost,CastingMode,spell_components

models={}
for m in ('off','v1','v2'):
 with open(f'.cache/no_cavern_{m}_table.pkl','rb') as f:d=pickle.load(f)
 models[m]=ComponentTable(ManaSpace(d['bounds'],d['land_count']),d['costs'],d['weights'],d['rows'])
space=models['v2'].space
ns=dict(Spell=Spell,SpellCost=SpellCost,CastingMode=CastingMode)
exec(json.loads(Path('.cache/no_cavern_inputs.json').read_text())['sultai-inputs'],ns)
output={'penalties':[],'weights':[],'stress':[]}
def compare(tables,weights=None,shock=F(14,1000),town=F(1,100)):
 scored={m:t.score(weights,shock_penalty=shock,town_penalty=town) for m,t in tables.items()}
 winners={m:s.table.rows[s.winner_index].counts for m,s in scored.items()}
 result={}
 for m,s in scored.items():
  best=s.score_numbers[s.winner_index]
  result[m]={'counts':winners[m],'score':float(F(best,s.denominator)),'cross':{}}
  for origin,counts in winners.items():
   n=s.score_numbers[s.table._indices[counts]]
   result[m]['cross'][origin]={'loss':float(F(best-n,s.denominator)),'percent':100*float(F(best-n,best)) if best else 0,
     'rank':1+sum(x>n for x in s.score_numbers),'swaps':sum(abs(a-b) for a,b in zip(winners[m],counts))//2}
 return result
for shock in (0,.007,.014,.028,.05):
 for town in (0,.005,.01,.02,.04):
  output['penalties'].append(dict(shock=shock,town=town,results=compare(models,shock=shock,town=town)))
print('penalty grid complete',flush=True)
for label,weight in [('cheap_double',lambda mv:2 if mv<=2 else 1),('expensive_double',lambda mv:2 if mv>=4 else 1)]:
 weights={c:weight(int(c.rstrip('WUBRG') or 0)+sum(x in 'WUBRG' for x in c)) for c in models['v2'].costs}
 output['weights'].append(dict(label=label,results=compare(models,weights)))
# Exactly reweight physical spell modes without changing physical deck slots.
_,original,_=spell_components(ns['SPELLS'])
for label,prefer in [('early_modes',lambda mv: mv<=2),('late_modes',lambda mv:mv>=4)]:
 changed=[]
 for spell in ns['SPELLS']:
  if isinstance(spell,Spell):
   modes=tuple(CastingMode(m.cost,2 if prefer(int(m.cost.rstrip('WUBRG') or 0)+sum(c in 'WUBRG' for c in m.cost)) else 1) for m in spell.modes)
   changed.append(Spell(spell.count,modes,spell.weight))
  else:changed.append(spell)
 _,_,weighted=spell_components(changed)
 weights={c:weighted[c]/original[c] for c in original}
 output['weights'].append(dict(label=label,results=compare(models,weights)))
Path('.cache/robustness_results.json').write_text(json.dumps(output,indent=2))

# Correlation-only stress: at most one drawn land fails. Preserve per-land
# failure probability 1/T when k<=T; cap it at 1/k when k>T. Keep optimistic
# selection from all seen lands, so this is NOT a complete sequencing model.
def correlated(sources,totals,valid,total,max_drawn,seen_by_turn,nonlands,deck_size):
 counts=tuple(np.indices(valid.shape,sparse=True)); entries=[]
 for turn,seen in seen_by_turn:
  if turn<total:continue
  risky=np.zeros(valid.shape,dtype=np.int64);lost=np.zeros(valid.shape,dtype=np.int64)
  for axis,(source,count) in enumerate(zip(sources,counts)):
   if batch.land_availability(source.kind,turn)==1:continue
   risky+=count
   shifted=np.zeros_like(valid);dst=[slice(None)]*valid.ndim;src=dst.copy()
   dst[axis]=slice(1,None);src[axis]=slice(None,-1)
   shifted[tuple(dst)]=valid[tuple(src)]
   lost+=count*shifted
  denom=np.maximum(totals,turn)
  numerator=valid*(denom-risky)+lost
  factors=[F(comb(nonlands-1,seen-k-1),comb(deck_size,seen)*len(seen_by_turn)*max(turn,k))
           if 0<=seen-k-1<nonlands else F() for k in range(max_drawn+1)]
  entries.append((numerator,factors))
 denominator=lcm(*(f.denominator for _,fs in entries for f in fs))
 values=np.zeros(valid.shape,dtype=object)
 for numerator,fs in entries:
  lookup=np.array([f.numerator*(denominator//f.denominator) for f in fs]+[0]*(sum(s-1 for s in valid.shape)-max_drawn),dtype=object)
  values+=numerator*lookup[totals]
 return values,denominator
start=perf_counter()
with patch('mana_batch._opportunity_grid',correlated):
 corr=build_component_table(space,ns['SPELLS'],backend='batch')
output['stress'].append(dict(label='single_failure',seconds=perf_counter()-start,results=compare(dict(models,alternative=corr))))
print('correlated complete',output['stress'][-1]['seconds'],flush=True)
for m,path in (('v1','.cache/mana_batch_separate.py'),('v2','mana_batch.py')):
 source=Path(path).read_text().replace('if set(other.types).intersection(rule.requires):','if False:  # stress: Verge secondary never enabled')
 target=Path(f'.cache/stress_no_verge_{m}.py');target.write_text(source)
 spec=importlib.util.spec_from_file_location('stress_'+m,target);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 start=perf_counter()
 with patch('mana_batch.component_columns',module.component_columns):
  t=build_component_table(space,ns['SPELLS'],backend='batch')
 models['no_verge_'+m]=t
 print('no verge',m,perf_counter()-start,flush=True)
output['stress'].append(dict(label='no_verge_secondary',results=compare({m:models['no_verge_'+m] for m in ('v1','v2')})))
Path('.cache/robustness_results.json').write_text(json.dumps(output,indent=2))
Path('reports/robustness_results.json').write_text(json.dumps(output,indent=2))
print('COMPLETE',flush=True)
