from examples.moonshadow_decay import *
space=make_space()
ev=LocalManaEvaluator(space,PROFILES,model=MANA_MODEL,half_life=2,family_maximums={'basic':2})
with open('.cache/moonshadow_decay_h2.pkl','rb') as f:sig,entries=pickle.load(f)
ev.restore_cache(sig,entries)
options=[]
for c in ev.cache:
 b=dict(zip(space.sources,c))
 if sum(n for s,n in b.items() if s.kind=='shock')==10:options.append(ev.value(b))
best=max(options,key=lambda r:r.raw_score)
base=dict(zip(space.sources,best.counts))
ce=LocalManaEvaluator(space,PROFILES,model=MANA_MODEL,half_life=2,family_maximums={'basic':2},family_totals={'shock':10})
r=local_search(ce,base,evaluation_budget=4000,shock_penalty=.003059364,town_penalty=TOWN,progress=lambda n,b:print(n,float(b.score),flush=True))
assert r.stopped=='two-land local optimum'
b=dict(zip(space.sources,r.best.counts))
data={'half_life':2,'horizon':9,'shock_penalty':.003059364,'town_penalty':TOWN,'constraint':'exactly 10 shocks; penalty tuning skipped this count','lands':named(b),'raw':float(r.best.raw_score),'score':float(r.best.score),'stop':r.stopped}
p=Path('reports/moonshadow_h2_10shocks')
p.with_suffix('.json').write_text(json.dumps(data,indent=2))
p.with_suffix('.txt').write_text('Deck\n'+'\n'.join(f'{n} {name}' for name,n in {**SPELL_COUNTS,**named(b)}.items())+'\n')
print(json.dumps(data),flush=True)
