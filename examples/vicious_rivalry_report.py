"""Validate and summarize completed Vicious Rivalry half-life runs."""
import json
from pathlib import Path

from examples.vicious_rivalry_sweep import COUNTS, NAMES, SPELLS, make_space
from examples.sultai import MANA_MODEL
from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.evaluation import evaluate
from mtg_tools.mana.space import ManaSpace


def main():
    original = make_space((0, 8))
    space = ManaSpace(
        {**original.bounds, **{ManaSource(p, 'tapped'): (0, 2) for p in ('UB', 'BG', 'UG')}},
        26, {**original.family_bounds, 'tapped': (2, 2)})
    inverse = {NAMES[s]: s for s in space.sources}
    reports = []
    for h in (1.0, 1.5, 2.0):
        path = Path(f'ideas/reports/vicious_rivalry_h{str(h).replace(".", "_")}.json')
        report = json.loads(path.read_text())
        base = {inverse[name]: count for name, count in report['lands'].items()}
        space.counts(base)
        assert sum(COUNTS.values()) + sum(base.values()) == 60
        assert all(r['attempts'][-1]['stop'] == 'two-land local optimum' for r in report['runs'])
        assert abs(evaluate(base, SPELLS, model=MANA_MODEL, half_life=h).score - report['score']) < 1e-12
        report['family_counts'] = {kind: sum(n for s, n in base.items() if s.kind == kind)
                                   for kind in sorted({s.kind for s in space.sources})}
        report['spell_counts'] = COUNTS
        report['source_bounds'] = {NAMES[s]: list(b) for s, b in space.bounds.items()}
        report['schema_version'] = 2
        report['card_text_source'] = 'https://www.mtg.wtf/card/sos/241/Vicious-Rivalry'
        path.write_text(json.dumps(report, indent=2) + '\n')
        reports.append(report)
    cross_scores = [[evaluate({inverse[k]: v for k, v in candidate['lands'].items()}, SPELLS,
                              model=MANA_MODEL, half_life=target['half_life']).score
                     for candidate in reports] for target in reports]
    for i, row in enumerate(cross_scores):
        assert max(row) <= reports[i]['score'] + 1e-12, (reports[i]['half_life'], row)
    lines = ['# Vicious Rivalry mana-base sweep', '',
             '26 lands; 0–8 shocks; exactly two untyped always-tapped duals. Four Caverns and four Starting Towns fixed; at most two basics. Fastlands, slowlands and Verges remain available.', '',
             '| Land | h=1 | h=1.5 | h=2 |', '| --- | ---: | ---: | ---: |']
    names = list(dict.fromkeys(name for r in reports for name in r['lands']))
    lines += [f'| {name} | ' + ' | '.join(str(r['lands'].get(name, 0)) for r in reports) + ' |' for name in names]
    lines += ['', '| Measure | h=1 | h=1.5 | h=2 |', '| --- | ---: | ---: | ---: |']
    for label, key in [('Raw score', 'score'), ('Horizon', 'horizon'), ('Omitted weight', 'omitted_mass')]:
        lines.append(f'| {label} | ' + ' | '.join(str(r[key]) for r in reports) + ' |')
    lines += ['', 'Scores use different turn weightings and should not be compared across columns. Each reported base completed the two-land local-optimum check; this is not a global certificate. UB/BG starts completed for all half-lives; the UG start completed only for h=1. The remaining UG searches were stopped at the user’s request. Winners were also evaluated under the other half-lives.', '',
              'The unfinished h=2 UG run reached 2.069816626315 (about 0.0014% above the delivered base), but was stopped before its land list was checkpointed. The delivered h=2 deck is the best saved, completed result.', '',
              'Full casting profiles and uniform mode shares retained. Cavern is unrestricted rainbow mana. Life payments, sequencing, mulligans and land abilities are outside the evaluator. Tapped dual entries are color placeholders for untyped duals/manlands.', '',
              'Vicious Rivalry uses 2BG: https://www.mtg.wtf/card/sos/241/Vicious-Rivalry', '',
              'Decklists: [h=1](vicious_rivalry_h1_0.txt), [h=1.5](vicious_rivalry_h1_5.txt), [h=2](vicious_rivalry_h2_0.txt).', '']
    Path('ideas/reports/vicious_rivalry_sweep.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'scores': [r['score'] for r in reports], 'cross_scores': cross_scores}))


if __name__ == '__main__':
    main()
