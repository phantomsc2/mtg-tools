"""Summarize bounded one-swap reruns against saved two-swap results."""
import json
from pathlib import Path


def main():
    reports = []
    lines = ['# Vicious Rivalry: one-swap-only rerun', '',
             'Same spell list, source pool, constraints, and UB/BG/UG starts as the previous search. '
             'Each call uses max_replacements=1 and a fixed 800-visit budget. '
             'The saved two-swap evaluation caches are reused, but search starts from the original seeds, not from cached winners.', '',
             '| h | One-swap score | Prior completed two-swap score | Score shortfall | Search seconds | Cache loading seconds | New evaluations |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for h in (1.0, 1.5, 2.0):
        tag = str(h).replace('.', '_')
        one = json.loads(Path(f'reports/vicious_rivalry_h{tag}_one_swap.json').read_text())
        two = json.loads(Path(f'reports/vicious_rivalry_h{tag}.json').read_text())
        assert one['max_replacements'] == 1
        assert len(one['runs']) == 3
        assert all(r['attempts'][-1]['stop'] == 'one-land local optimum' for r in one['runs'])
        assert sum(one['lands'].values()) == 26
        assert sum(one['spell_counts'].values()) == 34
        shortfall = (two['score'] - one['score']) / two['score']
        lines.append(f"| {h:g} | {one['score']:.12f} | {two['score']:.12f} | {shortfall:.4%} | "
                     f"{one['search_seconds']:.2f} | {one['cache_load_seconds']:.2f} | "
                     f"{sum(r['new_evaluations'] for r in one['runs'])} |")
        reports.append(one)
    lines += ['', 'All nine starts completed their full one-swap neighborhood checks below the visit cap. '
              'No two-swap checks were run. Timings are warm-cache measurements: UB/BG trajectories were already cached; '
              'the h=1.5 and h=2 UG trajectories required new evaluations. They are not directly comparable to cold earlier timings.', '',
              '| h / start | Score | Visits | New evaluations | Seconds |',
              '| --- | ---: | ---: | ---: | ---: |']
    for r in reports:
        for start in r['runs']:
            a = start['attempts'][-1]
            lines.append(f"| {r['half_life']:g} / {start['start']} | {start['score']:.12f} | "
                         f"{a['visits']} | {start['new_evaluations']} | {a['seconds']:.2f} |")
    lines += ['', '| Land | h=1 | h=1.5 | h=2 |', '| --- | ---: | ---: | ---: |']
    names = dict.fromkeys(name for r in reports for name in r['lands'])
    lines += [f'| {name} | ' + ' | '.join(str(r['lands'].get(name, 0)) for r in reports) + ' |' for name in names]
    lines += ['', 'Decklists: [h=1](vicious_rivalry_h1_0_one_swap.txt), '
              '[h=1.5](vicious_rivalry_h1_5_one_swap.txt), [h=2](vicious_rivalry_h2_0_one_swap.txt).', '',
              'Raw scores use different turn weights across h, so score differences are meaningful within each row, not across half-lives. '
              'Tapped entries are untyped dual/manland placeholders; land abilities are not valued.', '']
    Path('reports/vicious_rivalry_one_swap.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines[:9]))


if __name__ == '__main__':
    main()
