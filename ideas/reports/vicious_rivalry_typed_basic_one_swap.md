# Vicious Rivalry: typed tapped duals and a required basic

One-swap search only; 800 visits per start, without expansion. Three original UB/BG/UG seeds per half-life. 26 lands, 0–8 shocks, 1–2 basics, exactly two typed tapped duals; four Caverns and four Starting Towns fixed. Untyped tapped duals are excluded. Slowlands remain independently available. Surveil and land abilities are not valued.

| h | Raw score | Previous untyped/no-minimum one-swap score | Change | Search seconds | Completed starts |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 0.830259560474 | 0.828409576485 | +0.2233% | 184.6 | 3/3 |
| 1.5 | 1.460944035736 | 1.460791140662 | +0.0105% | 886.3 | 3/3 |
| 2 | 2.068520325287 | 2.069577356600 | -0.0511% | 1495.6 | 3/3 |

Changes combine the typed-dual substitution and the basic minimum; they do not isolate either change. Compare scores within each half-life, not across half-lives.

| Land | h=1 | h=1.5 | h=2 |
| --- | ---: | ---: | ---: |
| Swamp | 1 | 1 | 1 |
| Cavern of Souls | 4 | 4 | 4 |
| Watery Grave | 4 | 4 | 4 |
| Breeding Pool | 4 | 4 | 4 |
| Deathcap Glade | 2 | 2 | 3 |
| Starting Town | 4 | 4 | 4 |
| Hedge Maze | 2 | 2 | 2 |
| Wastewood Verge | 2 | 2 | 1 |
| Gloomlake Verge | 3 | 2 | 2 |
| Shipwreck Marsh | 0 | 1 | 1 |

| h / start | Score | Visits | New evaluations | Seconds | Stop |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 / UB | 0.829188659022 | 194 | 194 | 42.6 | one-land local optimum |
| 1 / BG | 0.830259560474 | 323 | 323 | 78.2 | one-land local optimum |
| 1 / UG | 0.829929779849 | 247 | 243 | 63.8 | one-land local optimum |
| 1.5 / UB | 1.460630434673 | 568 | 568 | 353.6 | one-land local optimum |
| 1.5 / BG | 1.460944035736 | 476 | 476 | 276.1 | one-land local optimum |
| 1.5 / UG | 1.460547849886 | 404 | 399 | 256.6 | one-land local optimum |
| 2 / UB | 2.067603073449 | 585 | 585 | 620.4 | one-land local optimum |
| 2 / BG | 2.068520325287 | 476 | 474 | 441.6 | one-land local optimum |
| 2 / UG | 2.067906723485 | 487 | 477 | 433.6 | one-land local optimum |

Each winning score was independently re-evaluated when its worker finished. One-land local optima are not two-land or global certificates. A budget-limited start is explicitly labeled above.

Decklists: [h=1](vicious_rivalry_h1_0_typed_basic1_one_swap.txt), [h=1.5](vicious_rivalry_h1_5_typed_basic1_one_swap.txt), [h=2](vicious_rivalry_h2_0_typed_basic1_one_swap.txt).
