# Sultai optimization with at most two Opulent Palaces

Best found by deterministic bounded local search; no global-optimum claim.

| Land | Initial | Result |
| --- | ---: | ---: |
| Breeding Pool | 3 | 4 |
| Cavern of Souls | 4 | 4 |
| Gloomlake Verge | 4 | 4 |
| Island | 0 | 1 |
| Opulent Palace | 1 | 0 |
| Overgrown Tomb | 3 | 1 |
| Starting Town | 4 | 4 |
| Swamp | 1 | 1 |
| Wastewood Verge | 2 | 3 |
| Watery Grave | 4 | 3 |
| Willowrush Verge | 0 | 1 |
| **Total** | **26** | **26** |

Score: 3.068791946 → 3.083163704 (delta +0.014371757). These are opportunity scores, not win rates.

366 distinct bases evaluated in 217.85s. Filtered pool contains 2,050,095 compositions; no global grid was built.

OUT: 2 Overgrown Tomb, 1 Watery Grave, 1 Opulent Palace

IN: 1 Island, 1 Breeding Pool, 1 Wastewood Verge, 1 Willowrush Verge

| Initial Palaces | Budget | Visits | Seconds | Stop | Score |
| ---: | ---: | ---: | ---: | --- | ---: |
| 1 | 200 | 200 | 134.22 | evaluation budget | 3.083163704 |
| 0 | 150 | 150 | 49.84 | evaluation budget | 3.082301352 |
| 2 | 150 | 150 | 33.79 | evaluation budget | 3.082301352 |

## Per-cost weighted opportunities

| Cost | Initial | Result | Delta |
| --- | ---: | ---: | ---: |
| 1B | 0.606696130 | 0.600395411 | -0.006300719 |
| 1UBB | 0.088318177 | 0.087394984 | -0.000923194 |
| 1UU | 0.160661104 | 0.163163756 | +0.002502652 |
| 1UUB | 0.087858231 | 0.088635500 | +0.000777268 |
| 1UUGG | 0.042199959 | 0.042810232 | +0.000610273 |
| 2BG | 0.176865468 | 0.177964006 | +0.001098538 |
| 2G | 0.491827046 | 0.493867258 | +0.002040212 |
| 2UB | 0.088732932 | 0.089381635 | +0.000648703 |
| 2UU | 0.117316121 | 0.118917408 | +0.001601287 |
| 2UUBB | 0.020138030 | 0.020490945 | +0.000352915 |
| 2WWBB | 0.013663907 | 0.013261234 | -0.000402673 |
| 3GG | 0.042287336 | 0.042839327 | +0.000551991 |
| 3UU | 0.042949022 | 0.043596658 | +0.000647635 |
| 4BB | 0.040287717 | 0.041005336 | +0.000717618 |
| 4UU | 0.020140557 | 0.020531997 | +0.000391440 |
| 4WW | 0.013778127 | 0.013982395 | +0.000204269 |
| 7UU | 0.000000000 | 0.000000000 | +0.000000000 |
| BB | 0.231248355 | 0.216685848 | -0.014562507 |
| GG | 0.106590847 | 0.105728258 | -0.000862589 |
| UBG | 0.488266089 | 0.486569057 | -0.001697031 |
| UU | 0.229021239 | 0.233246433 | +0.004225195 |
| UUBB | 0.086869045 | 0.085613152 | -0.001255893 |
| WW | 0.053076506 | 0.053082873 | +0.000006367 |

## Settings and assumptions

```json
{
  "land_count": 26,
  "colors": "UBG",
  "format": "standard",
  "turns": 7,
  "position": "both",
  "opening_hand_size": 7,
  "shock_penalty": 0.012,
  "town_penalty": 0.015,
  "budgets": [
    200,
    150,
    150
  ],
  "palace_limit": 2
}
```

- V1: seen-land color coverage and independent land availability are separate.
- Cavern is unrestricted rainbow mana; creature and chosen-type restrictions are ignored.
- Incarnation modes target enters effects, omitting mixed evoke payments with no effect.
- Spider-Man includes colored-payment scenarios for copied incarnation effects.
- Sunderflock scenarios: 7UU, 2UU, 1UU; board presence is not simulated.
- Mode shares and spell importance are uniform; Overlord uses impending 1B only.
- No sequencing, mulligans, life simulation, or global-optimum guarantee.

Standard snapshot checked as of 2026-11-07.

Legality evidence: [Standard sets](https://magic.wizards.com/en/formats/standard), [TDM checklist](https://media.wizards.com/ContentResources/WPN/deck_checklists/tdm/MTGTDM_EN_DkCklst.pdf).
