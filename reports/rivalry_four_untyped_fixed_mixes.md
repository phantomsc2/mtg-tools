# Fixed untyped tapped dual mixes

Latest supplied Rivalry spell counts; four Caverns, four Towns, 1-2 basics, 0-8 shocks, 26 lands. Both requested mixes evaluated at h=1.5 and h=2. All four runs completed one-swap local-optimum checks below 800 visits. Non-mana abilities and Cavern restrictions are not modeled.

| Land | h=1.5: 3BG+1UB | h=1.5: 4BG | h=2: 3BG+1UB | h=2: 4BG |
| --- | ---: | ---: | ---: | ---: |
| Island | 1 | 1 | 0 | 0 |
| Cavern of Souls | 4 | 4 | 4 | 4 |
| Overgrown Tomb | 1 | 0 | 0 | 0 |
| Watery Grave | 3 | 4 | 4 | 4 |
| Breeding Pool | 4 | 4 | 4 | 4 |
| Deathcap Glade | 2 | 1 | 2 | 1 |
| BG tapped dual | 3 | 4 | 3 | 4 |
| UB tapped dual | 1 | 0 | 1 | 0 |
| Starting Town | 4 | 4 | 4 | 4 |
| Gloomlake Verge | 3 | 2 | 2 | 2 |
| Shipwreck Marsh | 0 | 1 | 0 | 1 |
| Wastewood Verge | 0 | 1 | 0 | 0 |
| Swamp | 0 | 0 | 1 | 1 |
| Dreamroot Cascade | 0 | 0 | 1 | 1 |

| h | Fixed mix | Score | Search seconds |
| --- | --- | ---: | ---: |
| 1.5 | {'UB': 1, 'BG': 3, 'UG': 0} | 1.434538124949 | 157.2 |
| 1.5 | {'UB': 0, 'BG': 4, 'UG': 0} | 1.434550083186 | 134.9 |
| 2.0 | {'UB': 1, 'BG': 3, 'UG': 0} | 2.026644389610 | 140.3 |
| 2.0 | {'UB': 0, 'BG': 4, 'UG': 0} | 2.026762277652 | 216.6 |

These scores slightly exceed the earlier free-color results within the respective half-lives. Constraints did not improve the global optimum; changed starting compositions reached better local basins. No global or two-swap certification. Winning scores were independently re-evaluated.
