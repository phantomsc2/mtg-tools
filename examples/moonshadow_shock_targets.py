"""Find penalties selecting eight and ten shocks for each half-life."""
from examples.moonshadow_decay import *

def search(h):
 ev=LocalManaEvaluator(make_space(),PROFILES,model=MANA_MODEL,half_life=h,family_maximums={'basic':2})
 cache=Path(f'.cache/moonshadow_decay_h{h}.pkl')
 with cache.open('rb') as f: sig,entries=pickle.load(f)
 ev.restore_cache(sig,entries)
 original={s:INITIAL.get(NAMES[s],0) for s in ev.space.sources}
 initial=json.loads(Path(f'reports/moonshadow_decay_h{h}.json').read_text())['lands']
 current={s:initial.get(NAMES[s],0) for s in ev.space.sources}
 raw_cache={}
 def strongest(penalty):
  for c in ev.cache:
   if c not in raw_cache:
    b=dict(zip(ev.space.sources,c))
    raw_cache[c]=(ev.value(b).raw_score,sum(n for source,n in b.items() if source.kind=='shock'))
  c=max(raw_cache,key=lambda c:raw_cache[c][0]-Fraction(str(penalty))*raw_cache[c][1])
  return dict(zip(ev.space.sources,c))
 for target in (8,10):
  lo,hi=0.,.008
  for step in range(24):
   penalty=round((lo+hi)/2,12)
   runs=[]
   for base in (strongest(penalty),current,original):
    budget=2000
    while True:
     r=local_search(ev,base,evaluation_budget=budget,shock_penalty=penalty,town_penalty=TOWN)
     base=dict(zip(ev.space.sources,r.best.counts))
     if r.stopped=='two-land local optimum':break
     budget*=2
    runs.append(r)
   winner=max((r.best for r in runs),key=lambda r:r.score)
   current=dict(zip(ev.space.sources,winner.counts))
   count=sum(n for s,n in current.items() if s.kind=='shock')
   print(f'h={h} target={target} penalty={penalty} shocks={count}',flush=True)
   with cache.open('wb') as f:pickle.dump((ev.cache_signature,dict(ev.cache)),f)
   if count==target:
    stem=Path(f'reports/moonshadow_h{h}_{target}shocks')
    data={'half_life':h,'horizon':ev.timing.horizon,'omitted_mass':ev.timing.omitted_mass,'shock_penalty':penalty,'town_penalty':TOWN,'lands':named(current),'score':float(winner.score),'raw':float(winner.raw_score),'runs':[{'stop':r.stopped,'score':float(r.best.score),'visits':r.evaluations} for r in runs]}
    stem.with_suffix('.json').write_text(json.dumps(data,indent=2))
    stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{n} {name}' for name,n in {**SPELL_COUNTS,**named(current)}.items())+'\n')
    break
   if count>target:lo=penalty
   else:hi=penalty
  else:print(f'No unconstrained {target}-shock winner found at h={h}; see moonshadow_ten_shock_fallback for the constrained alternative',flush=True)

if __name__=='__main__':
 for h in (1,2):search(h)
