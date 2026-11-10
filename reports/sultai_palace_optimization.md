# Sultai optimization with at most two Opulent Palaces

Best found by deterministic bounded local search; no global-optimum claim.

| Land | Initial | Result |
| --- | ---: | ---: |
| Breeding Pool | 4 | 4 |
| Cavern of Souls | 4 | 4 |
| Gloomlake Verge | 3 | 3 |
| Island | 1 | 0 |
| Overgrown Tomb | 2 | 4 |
| Restless Cottage | 2 | 2 |
| Starting Town | 4 | 4 |
| Swamp | 1 | 0 |
| Wastewood Verge | 1 | 0 |
| Watery Grave | 3 | 4 |
| Willowrush Verge | 1 | 1 |
| **Total** | **26** | **26** |

Score: 3.147665552 → 3.167769539 (delta +0.020103987). These are opportunity scores, not win rates.

297 distinct bases evaluated in 171.96s. Filtered pool contains 934,725 compositions; no global grid was built.

OUT: 1 Swamp, 1 Island, 1 Wastewood Verge

IN: 2 Overgrown Tomb, 1 Watery Grave

| Initial Palaces | Budget | Visits | Seconds | Stop | Score |
| ---: | ---: | ---: | ---: | --- | ---: |
| 0 | 200 | 200 | 96.73 | evaluation budget | 3.167769539 |
| 1 | 150 | 150 | 39.41 | evaluation budget | 3.163741892 |
| 2 | 150 | 150 | 35.82 | evaluation budget | 3.156562171 |

## Per-cost weighted opportunities

| Cost | Initial | Result | Delta |
| --- | ---: | ---: | ---: |
| 1B | 0.300970774 | 0.302512026 | +0.001541251 |
| 1UBB | 0.086692772 | 0.087379492 | +0.000686720 |
| 1UU | 0.159687444 | 0.159687444 | +0.000000000 |
| 1UUB | 0.087134979 | 0.087168950 | +0.000033971 |
| 1UUGG | 0.041846145 | 0.042109238 | +0.000263093 |
| 2BG | 0.175324470 | 0.175602419 | +0.000277949 |
| 2G | 0.489778719 | 0.491274641 | +0.001495922 |
| 2UB | 0.087910357 | 0.087944329 | +0.000033971 |
| 2UU | 0.116243492 | 0.116243492 | +0.000000000 |
| 2UUBB | 0.019749422 | 0.019755724 | +0.000006302 |
| 2WWBB | 0.012521559 | 0.012793338 | +0.000271779 |
| 3GG | 0.041927656 | 0.042190749 | +0.000263093 |
| 3UU | 0.042363174 | 0.042363174 | +0.000000000 |
| 4BB | 0.039509030 | 0.039521635 | +0.000012605 |
| 4UU | 0.019756892 | 0.019756892 | +0.000000000 |
| 4WW | 0.013039278 | 0.013039278 | +0.000000000 |
| 7UU | 0.000000000 | 0.000000000 | +0.000000000 |
| BB | 0.218719230 | 0.225728892 | +0.007009662 |
| GG | 0.105652527 | 0.109046170 | +0.003393642 |
| UBG | 0.727720832 | 0.731266584 | +0.003545752 |
| UU | 0.227713597 | 0.227713597 | +0.000000000 |
| UUBB | 0.085335841 | 0.086604114 | +0.001268273 |
| WW | 0.048067361 | 0.048067361 | +0.000000000 |

## Settings and assumptions

```json
{
  "land_count": 26,
  "colors": "UBG",
  "format": "standard",
  "turns": 7,
  "position": "both",
  "opening_hand_size": 7,
  "budgets": [
    200,
    150,
    150
  ],
  "palace_limit": 2
}
```

- Independent source outcomes jointly supply mana and colors; source limit equals turn.
- Verge colors use enabling types anywhere seen, including unavailable enablers.
- Cavern is unrestricted rainbow mana; creature and chosen-type restrictions are ignored.
- Incarnation modes target enters effects, omitting mixed evoke payments with no effect.
- Spider-Man includes colored-payment scenarios for copied incarnation effects.
- Sunderflock scenarios: 7UU, 2UU, 1UU; board presence is not simulated.
- Mode shares and spell importance are uniform; four Awaken and two Glarb, no Overlord.
- No sequencing, mulligans, life simulation, or global-optimum guarantee.

Standard snapshot checked as of 2026-11-07.

Legality evidence: [Standard sets](https://magic.wizards.com/en/formats/standard), [TDM checklist](https://media.wizards.com/ContentResources/WPN/deck_checklists/tdm/MTGTDM_EN_DkCklst.pdf).
