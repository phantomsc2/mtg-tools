# Moonshadow half-life 1: raw-score optimization

Horizon 5; omitted weight 3.1250%.
Score: 1.296916133144. Explicit family bounds: {'basic': (0, 2), 'shock': (0, 12), 'town': (4, 4)}.

| Land | Count |
| --- | ---: |
| Swamp | 1 |
| Cavern of Souls | 4 |
| Blooming Marsh | 2 |
| Overgrown Tomb | 4 |
| Watery Grave | 4 |
| Breeding Pool | 4 |
| Starting Town | 4 |
| Gloomlake Verge | 3 |

## Baselines under this weighting

| Base | Score |
| --- | ---: |
| supplied | 1.277720478035 |
| eight_shocks | 1.271321562633 |
| twelve_shocks | 1.290283677163 |
| strongest_cached | 1.296916133144 |

## Assumptions

- Full original casting profiles; uniform mode shares.
- No sequencing, mulligans or life totals; Cavern is unrestricted rainbow mana.
- Sultai slowlands are explicitly added outside the Standard snapshot.
- Best found two-land local optimum; no global-optimum guarantee.
