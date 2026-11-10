# Moonshadow half-life 2: raw-score optimization

Horizon 9; omitted weight 4.4194%.
Score: 2.444415796065. Explicit family bounds: {'basic': (0, 2), 'shock': (0, 12), 'town': (4, 4)}.

| Land | Count |
| --- | ---: |
| Cavern of Souls | 4 |
| Overgrown Tomb | 4 |
| Watery Grave | 4 |
| Breeding Pool | 4 |
| Shipwreck Marsh | 2 |
| Starting Town | 4 |
| Wastewood Verge | 1 |
| Gloomlake Verge | 3 |

## Baselines under this weighting

| Base | Score |
| --- | ---: |
| supplied | 2.426124991905 |
| eight_shocks | 2.432178342600 |
| twelve_shocks | 2.444415796065 |
| strongest_cached | 2.444415796065 |

## Assumptions

- Full original casting profiles; uniform mode shares.
- No sequencing, mulligans or life totals; Cavern is unrestricted rainbow mana.
- Sultai slowlands are explicitly added outside the Standard snapshot.
- Best found two-land local optimum; no global-optimum guarantee.
