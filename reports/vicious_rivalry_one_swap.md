# Vicious Rivalry: one-swap-only rerun

Same spell list, source pool, constraints, and UB/BG/UG starts as the previous search. Each call uses max_replacements=1 and a fixed 800-visit budget. The saved two-swap evaluation caches are reused, but search starts from the original seeds, not from cached winners.

| h | One-swap score | Prior completed two-swap score | Score shortfall | Search seconds | Cache loading seconds | New evaluations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.828409576485 | 0.828649878671 | 0.0290% | 1.46 | 15.26 | 0 |
| 1.5 | 1.460791140662 | 1.461113433798 | 0.0221% | 509.78 | 14.83 | 602 |
| 2 | 2.069577356600 | 2.069788169802 | 0.0102% | 895.54 | 13.14 | 601 |

All nine starts completed their full one-swap neighborhood checks below the visit cap. No two-swap checks were run. Timings are warm-cache measurements: UB/BG trajectories were already cached; the h=1.5 and h=2 UG trajectories required new evaluations. They are not directly comparable to cold earlier timings.

| h / start | Score | Visits | New evaluations | Seconds |
| --- | ---: | ---: | ---: | ---: |
| 1 / UB | 0.828204648816 | 390 | 0 | 0.40 |
| 1 / BG | 0.828409576485 | 360 | 0 | 0.43 |
| 1 / UG | 0.827984290618 | 574 | 0 | 0.63 |
| 1.5 / UB | 1.460300188928 | 540 | 0 | 0.95 |
| 1.5 / BG | 1.460791140662 | 420 | 0 | 0.71 |
| 1.5 / UG | 1.460557402035 | 602 | 602 | 508.13 |
| 2 / UB | 2.069349798082 | 548 | 0 | 1.18 |
| 2 / BG | 2.069358655242 | 470 | 0 | 1.11 |
| 2 / UG | 2.069577356600 | 601 | 601 | 893.25 |

| Land | h=1 | h=1.5 | h=2 |
| --- | ---: | ---: | ---: |
| Cavern of Souls | 4 | 4 | 4 |
| Watery Grave | 4 | 4 | 4 |
| Breeding Pool | 4 | 4 | 2 |
| Deathcap Glade | 2 | 2 | 3 |
| Shipwreck Marsh | 2 | 3 | 3 |
| BG tapped dual | 2 | 2 | 0 |
| Starting Town | 4 | 4 | 4 |
| Wastewood Verge | 1 | 1 | 0 |
| Gloomlake Verge | 2 | 1 | 0 |
| Willowrush Verge | 1 | 1 | 2 |
| Overgrown Tomb | 0 | 0 | 2 |
| UG tapped dual | 0 | 0 | 2 |

Decklists: [h=1](vicious_rivalry_h1_0_one_swap.txt), [h=1.5](vicious_rivalry_h1_5_one_swap.txt), [h=2](vicious_rivalry_h2_0_one_swap.txt).

Raw scores use different turn weights across h, so score differences are meaningful within each row, not across half-lives. Tapped entries are untyped dual/manland placeholders; land abilities are not valued.
