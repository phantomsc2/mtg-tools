# Sultai raw-score comparison: 8-10 shocks

Each shock count is an explicit search-space constraint. Scores measure casting opportunities.
Four Caverns, four Towns and two Cottages are fixed; basics total at most two; Palace at most two.

| Land | 8 shocks | 9 shocks | 10 shocks |
| --- | ---: | ---: | ---: |
| Breeding Pool | 4 | 4 | 4 |
| Cavern of Souls | 4 | 4 | 4 |
| Gloomlake Verge | 3 | 3 | 3 |
| Island | 1 | 0 | 0 |
| Overgrown Tomb | 1 | 1 | 2 |
| Restless Cottage | 2 | 2 | 2 |
| Starting Town | 4 | 4 | 4 |
| Swamp | 1 | 1 | 0 |
| Wastewood Verge | 2 | 2 | 2 |
| Watery Grave | 3 | 4 | 4 |
| Willowrush Verge | 1 | 1 | 1 |

| Shocks | Score | Stop |
| ---: | ---: | --- |
| 8 | 3.140236861277 | two-land local optimum |
| 9 | 3.149555367402 | two-land local optimum |
| 10 | 3.157366631264 | two-land local optimum |

A budget stop is not a local-optimum certificate. A complete run checks two-land replacements.
No sequencing, life totals, or Cavern restrictions are simulated.
Total runtime: 573.85s; budget 500 visits per count.
