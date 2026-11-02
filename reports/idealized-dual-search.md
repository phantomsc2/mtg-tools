# Idealized Sultai dual search

All 26 lands are unconditional U/B, B/G or U/G duals, with unlimited copies and no fixed Swamp.
The same 34 nonlands, 32 modes, uniform mode weights, equal play/draw weights and sufficient-land
conditioning remain in place. Life and tapped entry are ignored. No source produces white.

All 378 integer distributions were evaluated and ranked using exact integer/rational arithmetic.

| Rank | U/B | B/G | U/G | Success | Loss |
|---:|---:|---:|---:|---:|---:|
| 1 | 11 | 8 | 7 | 86.108241% | 13.891759% |
| 2 | 11 | 7 | 8 | 86.088278% | 13.911722% |
| 3 | 12 | 7 | 7 | 86.057696% | 13.942304% |
| 4 | 10 | 8 | 8 | 86.035830% | 13.964170% |
| 5 | 12 | 8 | 6 | 85.989596% | 14.010404% |
| 6 | 10 | 9 | 7 | 85.948902% | 14.051098% |
| 7 | 12 | 6 | 8 | 85.948669% | 14.051331% |
| 8 | 11 | 9 | 6 | 85.933250% | 14.066750% |
| 9 | 10 | 7 | 9 | 85.910235% | 14.089765% |
| 10 | 11 | 6 | 9 | 85.873619% | 14.126381% |

White requirements alone impose a loss floor of 8.529412%:
three of Emptiness's five modes and one of Spider-Man's eight modes are impossible.
Consequently the theoretical success ceiling is 91.470588%, even with perfect U/B/G access.

The CSV includes all distributions and exact success fractions.
Run `python mana_dual_search.py` with NumPy installed to regenerate.
