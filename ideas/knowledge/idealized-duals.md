# Unlimited Sultai duals

`mana_dual_search.py` ranks all 378 distributions of 26 lands across unconditional
U/B, B/G and U/G sources, without a fixed Swamp or copy limits. The same 34
nonlands and all 32 modes retain their original objective weights. White modes
remain present and fail with probability one. This pool is not a superset of
the earlier Town/Cavern pool, so its optimum need not score higher.

The optimum is 11 U/B, 8 B/G and 7 U/G, with exact rational success displayed
as 86.1082406147%. This supplies 18 U, 19 B and 15 G sources. No alternate
distribution ties its exact score. White requirements alone cause 8.5294117647
percentage points of loss (three of five Emptiness modes, one of eight Spider-Man
modes, four copies each among 34 nonlands). Remaining loss at the optimum is
5.3623476206 percentage points.

This evaluator enumerates drawn land count vectors up to 15 lands (the latest
evaluation sees 16 cards and requires a target nonland). For each legal deck,
precompute products of integer binomial coefficients. Hall's matching criterion
on drawn sources suffices because these duals have no conditional abilities;
unused drawn sources can be omitted to select exactly the mana-cost number
of lands. Nonland draw weights enforce target availability and enough lands.
All event sums fit int64 under comb(60, seen); aggregation and ranking use Python
integer numerators under a common rational denominator. Floats are display only.

All 20 tests pass, including exact agreement with the original scalar evaluator
for GG, BGU, BBUU, BUWW and 7UU. Results are written to
`reports/idealized-dual-search.md` and `.csv`.
