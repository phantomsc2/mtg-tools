# Sultai bases with 8-10 shocks and four Towns

Best found at each shock count for four Awaken, two Glarb and two Dellian Fels, without Overlords or Rapid Rescue.
Four Caverns, four Towns and two Restless Cottages are fixed; at most two basics total; Palace capped at two.

| Land | 8 shocks | 9 shocks | 10 shocks |
| --- | ---: | ---: | ---: |
| Breeding Pool | 4 | 4 | 4 |
| Cavern of Souls | 4 | 4 | 4 |
| Gloomlake Verge | 3 | 3 | 3 |
| Island | 1 | 1 | 1 |
| Overgrown Tomb | 1 | 1 | 2 |
| Restless Cottage | 2 | 2 | 2 |
| Starting Town | 4 | 4 | 4 |
| Swamp | 1 | 0 | 0 |
| Wastewood Verge | 2 | 2 | 1 |
| Watery Grave | 3 | 4 | 4 |
| Willowrush Verge | 1 | 1 | 1 |

| Shocks | Raw opportunities | Score at 0.012 | Shock penalty interval | Stop |
| ---: | ---: | ---: | --- | --- |
| 8 | 3.163460129 | 3.007460129 | 0.007820833 to unbounded | one-land local optimum |
| 9 | 3.171280961 | 3.003280961 | 0.006047422 to 0.007820833 | one-land local optimum |
| 10 | 3.177328383 | 2.997328383 | 0.000000000 to 0.006047422 | one-land local optimum |

ASCII scoring equation:

```text
score = raw_opportunities - shock_count * shock_penalty - 4 * town_penalty
```

Town penalty is 0.015. Because Town count is fixed, it does not affect shock-count crossings.
Intervals are exact for the reported representatives. Searches do not certify global optima.
A one-land local optimum checks transfers preserving the shock total; coupled two-transfer moves are not checked.
Restless Cottage uses the untyped tapped BG source; animation, Food, and graveyard effects are not scored.
V1 availability, unrestricted Cavern, uniform mode weights, and board scenarios remain in effect.

Total runtime: 90.53s. Budget: 500 visits per shock count.
