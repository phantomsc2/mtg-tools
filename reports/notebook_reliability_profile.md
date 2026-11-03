# Notebook reliability comparison

## Exact workload

Inputs were read from the current notebook and frozen before starting. The input
source and raw measurements are saved in [notebook_reliability_results.json](notebook_reliability_results.json).

- 60-card deck: 26 lands and 34 physical nonlands, including the notebook's
  multimode spell profiles. 21 canonical costs; 7UU is beyond the seven-turn
  horizon and correctly contributes zero in every model.
- Colors UBG; Standard snapshot 2026-11-03.
- Families shock, fast, Verge, Town, Cavern; each source ranges from 0 to 4.
  Fast lands are Blooming Marsh and Botanical Sanctum; Darkslick Shores is excluded.
- 10 source axes, 363,165 legal candidate compositions, 9,765,625 capacity-grid cells.
- Seven turns, both play/draw, opening hand seven; exact batch construction.
  Construction takes no baseline. Notebook penalties 0.014 shock / 0.01 Town
  are applied only at scoring time and do not affect this build benchmark.

## Full exhaustive builds

Each model ran once without cProfile in its own fresh Python process, sequentially
in off/v1/v2 order. Imports and input parsing were outside the timer. Timings
include complete component-table construction and row assembly; scoring,
rankings, sensitivity queries, and notebook HTML rendering are excluded.
Memory is Windows process peak resident working set, including Python/NumPy
and the completed table. Results are measured single runs, not medians.

| Model | Build time | Minutes | Relative time | Peak process memory |
| --- | ---: | ---: | ---: | ---: |
| Reliability off | 83.57 s | 1m 24s | 1.00x | 1.58 GiB |
| V1 separate factors | 219.23 s | 3m 39s | 2.62x | 2.08 GiB |
| V2 joint payment | 378.50 s | 6m 18s | 4.53x | 2.30 GiB |

All three builds are under the 15-minute target. V2 costs
1.73x V1 time on this workload,
adding 159.3s and
224 MiB peak memory.
Against reliability off, V2 adds 294.9s.

These are local sequential measurements. Later V2 costs showed variation
(roughly 11-28 seconds per active cost), so do not interpret the ratios as
hardware-independent constants. The smaller reference's V2 speed advantage
over V1 does not carry over to this setup.

## Representative full-grid profiles

To avoid repeating three complete large builds, detailed cProfile runs used
three costs (UUBB, 1B, UBG) with the same source bounds, grid, candidate list,
physical nonland count, and exact copy shares from the full spell profile.
These profiles call component-column construction directly and exclude final
full-table row assembly. They are diagnostic timings, not the full-build
numbers above. Each profile also ran in a fresh process.

| Cumulative work | Off | V1 | V2 |
| --- | ---: | ---: | ---: |
| Profiled workload | 19.09 s | 52.57 s | 89.04 s |
| Weighted opportunity grids | bypassed | 6.49 s | 43.89 s |
| Joint availability transforms (within grids) | bypassed | n/a | 39.14 s |
| Integer-limb transforms | 6.53 s / 6 calls | 21.13 s / 18 calls | 20.83 s / 18 calls |

Cumulative entries overlap; do not add grid time and its nested transform time.
V1's extra precision triples the limb-transform count on these costs. V2 performs
that same outer transform work, plus joint successful-source averaging. There
are three unreliable source axes here (two fast lands and Town); the previous
small reference had only one. V2's arbitrary-precision axis transforms dominate
its extra cost: about 39 seconds of the representative profile. Unlike the
small reference, V2 does not reduce the outer limb-transform count here.

Promising optimization targets are sharing joint availability transforms across
costs with matching payment masks, reducing arbitrary-precision grid arithmetic,
and exploiting the small number of distinct color/availability classes. None
were implemented as part of this comparison; all measured models remain exact
under their respective assumptions.

## Artifacts

- [Off profile](notebook_reliability_off_profile.txt)
- [V1 profile](notebook_reliability_v1_profile.txt)
- [V2 profile](notebook_reliability_v2_profile.txt)
- Raw inputs, measurements, and implementation hashes: [JSON](notebook_reliability_results.json).
- Local reproduction driver: `.cache/profile_notebook_reliability.py`.
- Local V1 implementation snapshot: `.cache/mana_batch_separate.py`.
- Full local profiles: `.cache/notebook_reliability_{off,v1,v2}.prof`.
