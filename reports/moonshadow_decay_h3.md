# Moonshadow half-life 3: raw-score optimization

Horizon 13; omitted weight 4.9606%.
Score: 3.494695712303. Explicit family bounds: {'basic': (0, 2), 'shock': (0, 12), 'town': (4, 4)}.

| Land | Count |
| --- | ---: |
| Cavern of Souls | 4 |
| Overgrown Tomb | 4 |
| Watery Grave | 4 |
| Breeding Pool | 4 |
| Deathcap Glade | 1 |
| Shipwreck Marsh | 2 |
| Starting Town | 4 |
| Gloomlake Verge | 3 |

## Baselines under this weighting

| Base | Score |
| --- | ---: |
| supplied | 3.475197040484 |
| eight_shocks | 3.485985742370 |
| twelve_shocks | 3.494158291808 |
| strongest_cached | 3.488014180009 |

## Assumptions

- Full original casting profiles; uniform mode shares.
- No sequencing, mulligans or life totals; Cavern is unrestricted rainbow mana.
- Sultai slowlands are explicitly added outside the Standard snapshot.
- Best found two-land local optimum; no global-optimum guarantee.
