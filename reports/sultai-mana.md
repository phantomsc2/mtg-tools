# Sultai evoke: exact conditional color coverage

Deck: 60 cards, 26 lands. Main deck only.

Each percentage is P(payment possible | target seen, lands seen >= total cost).
Seven-card keeps; see T+6 cards on the play or T+7 on the draw. Choose up to T lands, including unused Verge enablers.
Each column is evaluated on that turn. — means the cost exceeds the turn's land limit; N/A means an empty conditioning event.
Ignore draw order, ETB tapped, life and nonmana costs, targets, ramp, extra draws and mulligans.
Cavern supplies any creature color, but only colorless for noncreatures. Verge conditions remain active.
Single-effect rows include payments enabling both effects; rows overlap and must not be added.
Sunderflock scenarios assume the stated board without modeling its setup or conditioning on enabler draws.
Spider-Man copy scenarios assume the elemental is in a graveyard; condition on Spider-Man seen, not the copied card.
At four mana, Spider-Man can enable both Deceit effects, but cannot enable both Wistfulness or both Emptiness effects.
Copying Moonshadow or Sunderflock adds no color requirement beyond Spider-Man's normal row.
Sunderflock costs 7UU, 6UU, 2UU, 1UU and UU assume greatest Elemental MV 0, 1, 5, 6 and 9 respectively.
CSV includes exact reduced fractions and integer event weights per turn. Percentages alone are rounded to at most one decimal.

## On the play

| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---:|---:|---:|---:|---:|---:|
| Superior Spider-Man | 2UB | — | — | — | 99.7% | 99.7% | 99.8% |
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 98.1% | 98.5% | 98.8% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 97.2% | 97.7% | 98.2% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 95.1% | 96% | 96.8% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 97.2% | 97.7% | 98.2% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 89.2% | 90.8% | 92.4% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 98.1% | 98.5% | 98.8% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 27.5% | 30.6% | 34% |
| Deceit | UU | — | 81.8% | 86.1% | 89.7% | 92.6% | 94.8% |
| Deceit | BB | — | 81.6% | 88% | 91.2% | 93.8% | 95.7% |
| Deceit | 4UU | — | — | — | — | — | 99.9% |
| Deceit | 4BB | — | — | — | — | — | 99.9% |
| Deceit | 2UUBB | — | — | — | — | — | 99.8% |
| Wistfulness | GG | — | 64% | 73.1% | 78.7% | 83.6% | 87.6% |
| Wistfulness | UU | — | 81.8% | 86.1% | 89.7% | 92.6% | 94.8% |
| Wistfulness | 3GG | — | — | — | — | 96.3% | 96.8% |
| Wistfulness | 3UU | — | — | — | — | 99.4% | 99.5% |
| Wistfulness | 1GGUU | — | — | — | — | 95.7% | 96.3% |
| Emptiness | WW | — | 16.5% | 20% | 23.9% | 28% | 32.3% |
| Emptiness | BB | — | 81.6% | 88% | 91.2% | 93.8% | 95.7% |
| Emptiness | 4WW | — | — | — | — | — | 48.3% |
| Emptiness | 4BB | — | — | — | — | — | 99.9% |
| Emptiness | 2WWBB | — | — | — | — | — | 47.4% |
| Formidable Speaker | 2G | — | — | 97.4% | 98% | 98.4% | 98.8% |
| Bitter Triumph | 1B | — | 93.8% | 95.3% | 96.5% | 97.5% | 98.2% |
| Moonshadow | B | 89.2% | 94% | 96% | 97.4% | 98.3% | 98.9% |
| Awaken the Honored Dead | BGU | — | — | 85.1% | 88.1% | 90.8% | 93% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 97.6% | 98% | 98.4% |
| Sunderflock | 1UU | — | — | 92.5% | 94% | 95.4% | 96.5% |
| Sunderflock | UU | — | 81.8% | 86.1% | 89.7% | 92.6% | 94.8% |

## On the draw

| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---:|---:|---:|---:|---:|---:|
| Superior Spider-Man | 2UB | — | — | — | 99.7% | 99.8% | 99.8% |
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 98.5% | 98.8% | 99% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 97.7% | 98.2% | 98.6% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 96% | 96.8% | 97.5% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 97.7% | 98.2% | 98.6% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 90.8% | 92.4% | 93.8% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 98.5% | 98.8% | 99% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 30.6% | 34% | 37.7% |
| Deceit | UU | — | 86.1% | 89.7% | 92.6% | 94.8% | 96.4% |
| Deceit | BB | — | 85.6% | 91.2% | 93.8% | 95.7% | 97.1% |
| Deceit | 4UU | — | — | — | — | — | 99.9% |
| Deceit | 4BB | — | — | — | — | — | 99.9% |
| Deceit | 2UUBB | — | — | — | — | — | 99.8% |
| Wistfulness | GG | — | 70.2% | 78.7% | 83.6% | 87.6% | 90.8% |
| Wistfulness | UU | — | 86.1% | 89.7% | 92.6% | 94.8% | 96.4% |
| Wistfulness | 3GG | — | — | — | — | 96.8% | 97.2% |
| Wistfulness | 3UU | — | — | — | — | 99.5% | 99.6% |
| Wistfulness | 1GGUU | — | — | — | — | 96.3% | 96.8% |
| Emptiness | WW | — | 20% | 23.9% | 28% | 32.3% | 36.6% |
| Emptiness | BB | — | 85.6% | 91.2% | 93.8% | 95.7% | 97.1% |
| Emptiness | 4WW | — | — | — | — | — | 50% |
| Emptiness | 4BB | — | — | — | — | — | 99.9% |
| Emptiness | 2WWBB | — | — | — | — | — | 49.1% |
| Formidable Speaker | 2G | — | — | 98% | 98.4% | 98.8% | 99.1% |
| Bitter Triumph | 1B | — | 95.3% | 96.5% | 97.5% | 98.2% | 98.8% |
| Moonshadow | B | 92.2% | 96% | 97.4% | 98.3% | 98.9% | 99.3% |
| Awaken the Honored Dead | BGU | — | — | 88.1% | 90.8% | 93% | 94.9% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 98% | 98.4% | 98.7% |
| Sunderflock | 1UU | — | — | 94% | 95.4% | 96.5% | 97.5% |
| Sunderflock | UU | — | 86.1% | 89.7% | 92.6% | 94.8% | 96.4% |

## Mana-source inventory

| Land | Copies | Colors | Basic types | Condition |
|---|---:|---|---|---|
| Overgrown Tomb | 4 | BG | BG |  |
| Watery Grave | 4 | UB | UB |  |
| Swamp | 1 | B | B |  |
| Cavern of Souls | 2 | Any for creatures; C otherwise |  |  |
| Starting Town | 4 | WUBRG |  |  |
| Gloomlake Verge | 4 | U |  | B requires U or B type |
| Breeding Pool | 2 | UG | UG |  |
| Wastewood Verge | 2 | G |  | B requires B or G type |
| Willowrush Verge | 2 | U |  | G requires U or G type |
| Undercity Sewers | 1 | UB | UB |  |

Metadata and mathematical details: [analysis notes](../ideas/knowledge/mana-analysis.md).
