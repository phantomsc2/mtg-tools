"""Fixed 8..12 shock landscape at h=2, using complete one/two-land neighborhoods."""
from time import perf_counter

from examples.moonshadow_decay import *


def neighbors(space, counts, shocks, *, radius=2, basic_cap=2):
    """All eligible bases obtained by replacing up to radius lands, exact shock total."""
    evaluator = LocalManaEvaluator(space, (), model=MANA_MODEL, turns=1,
                                   family_totals={'shock': shocks},
                                   family_maximums={'basic': basic_cap})
    return evaluator.neighbor_counts(dict(zip(space.sources, counts)), max_replacements=radius)


def envelope(raw):
    """Exact penalty intervals where each fixed-count representative is optimal."""
    rows = {}
    for k, value in sorted(raw.items()):
        lower, upper = Fraction(), None
        for j, other in raw.items():
            if j > k:
                lower = max(lower, (other - value)/(j-k))
            elif j < k:
                bound = (value-other)/(k-j)
                upper = bound if upper is None else min(upper, bound)
        rows[k] = (lower, upper) if upper is None or lower <= upper else None
    return rows


def run(selected=None):
    started = perf_counter()
    space = make_space()
    # One common evaluator caches identical physical bases across fixed-count searches.
    # The generator enforces the exact count and all bounds before any evaluation.
    ev = LocalManaEvaluator(space, PROFILES, model=MANA_MODEL, half_life=2,
                            family_maximums={'basic': 2})
    cache_path = Path('.cache/moonshadow_decay_h2.pkl')
    with cache_path.open('rb') as stream:
        signature, entries = pickle.load(stream)
    ev.restore_cache(signature, entries)
    if selected is not None:
        cache_path = Path(f'.cache/moonshadow_landscape_{selected}.pkl')
        if cache_path.exists():
            with cache_path.open('rb') as stream:
                signature, entries = pickle.load(stream)
            ev.restore_cache(signature, entries)
    values = {}
    shock_indices = tuple(i for i, s in enumerate(space.sources) if s.kind == 'shock')

    def score(c):
        if c not in values:
            values[c] = ev.value(dict(zip(space.sources, c))).raw_score
        return values[c]

    def save_cache():
        # Atomic replacement protects the previously completed cache on interruption.
        temp = cache_path.with_suffix('.tmp')
        with temp.open('wb') as stream:
            pickle.dump((ev.cache_signature, dict(ev.cache)), stream)
        temp.replace(cache_path)

    def descend(c, k, radius, label):
        steps = []
        visited = set()
        while True:
            candidates = neighbors(space, c, k, radius=radius)
            best = c
            before = len(ev.cache)
            for index, candidate in enumerate(candidates):
                assert sum(candidate[i] for i in shock_indices) == k
                if score(candidate) > score(best) or (score(candidate) == score(best) and candidate < best):
                    best = candidate
                visited.add(candidate)
                if (index + 1) % 100 == 0:
                    print(f'k={k} {label} radius={radius} checked={index+1}/{len(candidates)} best_raw={float(score(best)):.9f}', flush=True)
            steps.append({'from': list(c), 'to': list(best), 'neighbors': len(candidates),
                          'new_evaluations': len(ev.cache)-before,
                          'improvement': float(score(best)-score(c))})
            save_cache()
            print(f'k={k} {label} radius={radius} complete raw={float(score(best)):.12f}', flush=True)
            if score(best) <= score(c):
                return c, steps, len(visited)
            c = best

    results = {}
    for k in (range(8, 13) if selected is None else (selected,)):
        # Strong, diverse starts selected deterministically from all historical bases.
        eligible = [c for c in ev.cache if sum(c[i] for i in shock_indices) == k]
        eligible.sort(key=lambda c: (-score(c), c))
        assert eligible, f'Missing cached seed at {k} shocks'
        seeds = [eligible[0]]
        pool = eligible[:min(250, len(eligible))]
        while len(seeds) < 3:
            choices = [c for c in pool if c not in seeds]
            if not choices:
                break
            seed = max(choices, key=lambda c: (min(sum(abs(a-b) for a,b in zip(c,s)) for s in seeds), score(c)))
            seeds.append(seed)
        runs = []
        checked = {}
        for index, seed in enumerate(seeds):
            c, single_steps, single_visits = descend(seed, k, 1, f'start{index+1}')
            if c not in checked:
                final, double_steps, double_visits = descend(c, k, 2, f'start{index+1}')
                checked[c] = (final, double_steps, double_visits)
            else:
                final, double_steps, double_visits = checked[c]
            runs.append({'start': named(dict(zip(space.sources, seed))),
                         'single_raw': float(score(c)), 'raw': float(score(final)),
                         'lands': named(dict(zip(space.sources, final))),
                         'single_steps': single_steps, 'double_steps': double_steps,
                         'single_visits': single_visits, 'double_visits': double_visits})
        winner = max((space.counts({s: r['lands'].get(NAMES[s], 0) for s in space.sources}) for r in runs),
                     key=score)
        result = {'raw': float(score(winner)), 'exact_raw': str(score(winner)),
                  'lands': named(dict(zip(space.sources, winner))), 'runs': runs,
                  'stop': 'complete radius-2 local optimum'}
        results[k] = result
        stem = Path(f'reports/moonshadow_h2_fixed_{k}shocks')
        stem.with_suffix('.txt').write_text('Deck\n'+'\n'.join(
            f'{n} {name}' for name,n in {**SPELL_COUNTS, **result['lands']}.items())+'\n')
        Path(f'reports/moonshadow_h2_landscape_part_{k}.json').write_text(json.dumps(result, indent=2))
        print(f'FINISHED k={k}: {json.dumps(result["lands"])} raw={result["raw"]:.12f}', flush=True)

    if selected is not None:
        return
    write_report(results, perf_counter()-started, len(ev.cache))


def write_report(results, seconds=None, cached_bases=None):
    raw = {k: Fraction(v['exact_raw']) for k,v in results.items()}
    intervals = envelope(raw)
    for k, result in results.items():
        interval = intervals[k]
        result['penalty_interval'] = None if interval is None else {
            'lower': float(interval[0]), 'upper': None if interval[1] is None else float(interval[1]),
            'exact_lower': str(interval[0]), 'exact_upper': str(interval[1])}
        result['marginal_raw_gain'] = None if k == 8 else float(raw[k]-raw[k-1])
        chord = raw[8] + Fraction(k-8,4)*(raw[12]-raw[8])
        result['above_8_12_chord'] = float(raw[k]-chord)
    report = {'settings': {'half_life':2,'horizon':9,'tail_tolerance':.05,'town_penalty':.015,
                            'shock_penalty':'zero during fixed-count optimization',
                            'fixed':{'Cavern of Souls':4,'Starting Town':4},'basic_cap':2,
                            'full_profiles':True,'starts':3,'radius':2},
              'results':results,'seconds':seconds,'cached_bases':cached_bases,
              'limitation':'Envelope among best-found 8..12-shock representatives; not a global optimum certificate.'}
    Path('reports/moonshadow_h2_landscape.json').write_text(json.dumps(report,indent=2))
    lines=['# h=2 fixed-shock landscape','',report['limitation'],'',
           '| Shocks | Raw opportunities | Marginal gain | Above 8-12 chord | Winning shock penalties |',
           '| ---: | ---: | ---: | ---: | --- |']
    for k,r in results.items():
        interval=r['penalty_interval']
        text='Never' if interval is None else f'{interval["lower"]:.12f} to '+ ('infinity' if interval['upper'] is None else f'{interval["upper"]:.12f}')
        marginal='-' if r['marginal_raw_gain'] is None else f'{r["marginal_raw_gain"]:.12f}'
        lines.append(f'| {k} | {r["raw"]:.12f} | {marginal} | {r["above_8_12_chord"]:+.12f} | {text} |')
    lines+=['','## Land counts','', '| Land | 8 | 9 | 10 | 11 | 12 |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for name in sorted(set().union(*(r['lands'] for r in results.values()))):
        lines.append('| '+name+' | '+' | '.join(str(results[k]['lands'].get(name,0)) for k in results)+' |')
    lines += ['', '## Method', '',
              'Three diverse cached starts per count; exact shock count enforced in candidate generation.',
              'Each run uses one-land descent followed by complete two-land descent, including coupled moves.',
              'All bounds and the two-basic cap are enforced. Four Caverns and four Towns remain fixed.',
              'Full original casting profiles; half-life 2, horizon 9; penalties are compared after optimizing raw opportunities.',
              'The fixed Town deduction is 0.06 for every base, so it does not affect crossings.', '',
              '## Decklists', '']
    lines += [f'- [{k} shocks](moonshadow_h2_fixed_{k}shocks.txt)' for k in results]
    if all(results[k]['above_8_12_chord'] < 0 for k in (9,10,11)):
        crossing = (raw[12]-raw[8])/4
        lines += ['', '## Penalty interpretation', '',
                  f'The endpoint crossing is {float(crossing):.12f}. Among these representatives, twelve shocks wins below it and eight wins above it; both tie at the crossing.',
                  'Nine, ten and eleven shocks lie strictly below the 8-to-12 chord and never win at a nonnegative linear shock penalty.',
                  'This reproduces a direct jump among best-found bases. Complete two-land local optimality and multi-start convergence do not certify a global optimum.']
    Path('reports/moonshadow_h2_landscape.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:{key:r[key] for key in ('raw','penalty_interval','marginal_raw_gain','above_8_12_chord')} for k,r in results.items()}),flush=True)


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, choices=range(8,13))
    parser.add_argument('--merge', action='store_true')
    args = parser.parse_args()
    if args.merge:
        results = {k: json.loads(Path(f'reports/moonshadow_h2_landscape_part_{k}.json').read_text()) for k in range(8,13)}
        write_report(results)
    else:
        run(args.count)
