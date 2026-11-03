# Optima without Cavern

Cavern was removed from the notebook's enabled family list. Inputs otherwise
retain the current deck, 26 lands, UBG, Standard filter, shock/fast/Verge/Town
0-4 bounds, seven turns, both positions, and opening hand seven. Each model
searches all **32,211** candidates on a **1,953,125**-cell grid, using 21 costs.
Scores below apply the notebook's shock penalty 0.014 and Town penalty 0.01.
No baseline is used. All three optima are unique.

## Winning compositions

| Source | Off | V1 separate | V2 joint |
| --- | ---: | ---: | ---: |
| fast:BG | 4 | 4 | 2 |
| fast:UG | 4 | 0 | 0 |
| shock:BG | 4 | 2 | 4 |
| shock:UB | 4 | 4 | 4 |
| shock:UG | 0 | 4 | 4 |
| town:WUBRG | 4 | 4 | 4 |
| verge:BG | 0 | 2 | 2 |
| verge:UB | 3 | 4 | 4 |
| verge:UG | 3 | 2 | 2 |
| **Total** | **26** | **26** | **26** |

## Builds and own-model scores

| Model | Build | Own optimum score | Optimal ties |
| --- | ---: | ---: | ---: |
| off | 8.76 s | 3.101938823 | 1 |
| v1 | 37.68 s | 3.009327531 | 1 |
| v2 | 74.80 s | 2.982574336 | 1 |

Build times are single fresh-process runs and exclude persistence and scoring.
Scoring plus top-ten selection took less than one second per model. Scores from
different models measure different approximations; compare candidate scores
within a model to judge the composition change.

## Cross-evaluation of winners

| Evaluated winner | Score under off | Score under V1 | Score under V2 | V2 rank |
| --- | ---: | ---: | ---: | ---: |
| off | 3.101938823 | 2.984070953 | 2.946231269 | 2657 |
| v1 | 3.086121370 | 3.009327531 | 2.980393601 | 8 |
| v2 | 3.062196321 | 3.005048796 | 2.982574336 | 1 |

Under V2, the V1 optimum ranks eighth and loses only 0.002180735 opportunities
versus the V2 optimum (about 0.0731% of its score). V2 replaces two Blooming Marsh
with two BG shocks; all other counts match V1. The off optimum ranks 2,657th
under V2 and loses 0.036343067 opportunities (about 1.22%). All ranks here are
one plus the number of strictly better scores.

The reduced pool allows all three complete builds in under 75 seconds each on
this machine. No further evaluator optimization was introduced. The detailed
joint-versus-separated profiling from the previous report remains separate.

## Retained data

[Inputs, top ten per model, exact scores, and cross-evaluations](no_cavern_optimization.json)
are saved durably in reports. Full exact component tables were also persisted:
`.cache/no_cavern_{off,v1,v2}_table.pkl`. Each trusted local pickle contains
bounds, land count, costs, default weights, and BaseComponents rows. Reconstruct
with `ComponentTable(ManaSpace(data['bounds'], data['land_count']), data['costs'],
data['weights'], data['rows'])`; no rebuild is needed. The local run driver is
`.cache/compare_no_cavern.py`, with frozen notebook inputs in
`.cache/no_cavern_inputs.json`.
