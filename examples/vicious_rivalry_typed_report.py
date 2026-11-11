"""Summarize one-swap Rivalry searches with typed tapped duals and 1–2 basics."""
import json
from pathlib import Path


def main():
    reports = []
    lines = ['# Vicious Rivalry: typed tapped duals and a required basic', '',
             'One-swap search only; 800 visits per start, without expansion. '
             'Three original UB/BG/UG seeds per half-life. 26 lands, 0–8 shocks, '
             '1–2 basics, exactly two typed tapped duals; four Caverns and four Starting Towns fixed. '
             'Untyped tapped duals are excluded. Slowlands remain independently available. '
             'Surveil and land abilities are not valued.', '',
             '| h | Raw score | Previous untyped/no-minimum one-swap score | Change | Search seconds | Completed starts |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for h in (1.0, 1.5, 2.0):
        tag = str(h).replace('.', '_')
        r = json.loads(Path(f'reports/vicious_rivalry_h{tag}_typed_basic1_one_swap.json').read_text())
        old = json.loads(Path(f'reports/vicious_rivalry_h{tag}_one_swap.json').read_text())
        assert r['max_replacements'] == 1 and len(r['runs']) == 3
        assert sum(r['lands'].values()) == 26 and sum(r['spell_counts'].values()) == 34
        assert r['family_counts']['typed_tapped'] == 2
        assert 1 <= r['family_counts']['basic'] <= 2
        assert r['family_counts']['shock'] <= 8
        assert all(a['visits'] <= 800 for run in r['runs'] for a in run['attempts'])
        done = sum(run['attempts'][-1]['stop'] == 'one-land local optimum' for run in r['runs'])
        lines.append(f"| {h:g} | {r['score']:.12f} | {old['score']:.12f} | "
                     f"{(r['score']/old['score']-1):+.4%} | {r['search_seconds']:.1f} | {done}/3 |")
        reports.append(r)
    lines += ['', 'Changes combine the typed-dual substitution and the basic minimum; '
              'they do not isolate either change. Compare scores within each half-life, not across half-lives.', '',
              '| Land | h=1 | h=1.5 | h=2 |', '| --- | ---: | ---: | ---: |']
    names = dict.fromkeys(name for r in reports for name in r['lands'])
    lines += [f'| {name} | ' + ' | '.join(str(r['lands'].get(name, 0)) for r in reports) + ' |' for name in names]
    lines += ['', '| h / start | Score | Visits | New evaluations | Seconds | Stop |',
              '| --- | ---: | ---: | ---: | ---: | --- |']
    for r in reports:
        for run in r['runs']:
            a = run['attempts'][-1]
            lines.append(f"| {r['half_life']:g} / {run['start']} | {run['score']:.12f} | "
                         f"{a['visits']} | {run['new_evaluations']} | {a['seconds']:.1f} | {a['stop']} |")
    lines += ['', 'Each winning score was independently re-evaluated when its worker finished. '
              'One-land local optima are not two-land or global certificates. A budget-limited start '
              'is explicitly labeled above.', '',
              'Decklists: [h=1](vicious_rivalry_h1_0_typed_basic1_one_swap.txt), '
              '[h=1.5](vicious_rivalry_h1_5_typed_basic1_one_swap.txt), '
              '[h=2](vicious_rivalry_h2_0_typed_basic1_one_swap.txt).', '']
    Path('reports/vicious_rivalry_typed_basic_one_swap.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
