# Sultai bases with 8-10 shocks and four Towns

Best found at each shock count; the evaluator and spell scenarios match the previous search.
Four Caverns and one Swamp remain fixed; Palace is capped at two.

| Land | 8 shocks | 9 shocks | 10 shocks |
| --- | ---: | ---: | ---: |
| Breeding Pool | 4 | 4 | 4 |
| Cavern of Souls | 4 | 4 | 4 |
| Gloomlake Verge | 4 | 4 | 4 |
| Island | 1 | 1 | 0 |
| Overgrown Tomb | 2 | 3 | 3 |
| Starting Town | 4 | 4 | 4 |
| Swamp | 1 | 1 | 1 |
| Wastewood Verge | 3 | 2 | 2 |
| Watery Grave | 2 | 2 | 3 |
| Willowrush Verge | 1 | 1 | 1 |

| Shocks | Raw opportunities | Score at 0.012 | Shock penalty interval | Stop |
| ---: | ---: | ---: | --- | --- |
| 8 | 3.338655725 | 3.182655725 | 0.009969531 to unbounded | one-land local optimum |
| 9 | 3.348625256 | 3.180625256 | 0.007673725 to 0.009969531 | one-land local optimum |
| 10 | 3.356298980 | 3.176298980 | 0.000000000 to 0.007673725 | one-land local optimum |

ASCII scoring equation:

```text
score = raw_opportunities - shock_count * shock_penalty - 4 * town_penalty
```

Town penalty is 0.015. Because Town count is fixed, it does not affect shock-count crossings.
Intervals are exact for the reported representatives. Searches do not certify global optima.
A one-land local optimum checks transfers preserving the shock total; coupled two-transfer moves are not checked.
The previous V1 availability, unrestricted Cavern, uniform mode weights, and board scenarios remain in effect.

Total runtime: 54.58s. Budget: 500 visits per shock count.
