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
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 97.4% | 97.8% | 98.2% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 96% | 96.7% | 97.3% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 93.7% | 94.8% | 95.8% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 96% | 96.7% | 97.3% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 88.1% | 89.8% | 91.3% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 97.4% | 97.8% | 98.2% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 0% | 0% | 0% |
| Deceit | UU | — | 78% | 82.9% | 87.1% | 90.5% | 93.1% |
| Deceit | BB | — | 81.8% | 86.1% | 89.7% | 92.6% | 94.8% |
| Deceit | 4UU | — | — | — | — | — | 99.7% |
| Deceit | 4BB | — | — | — | — | — | 99.9% |
| Deceit | 2UUBB | — | — | — | — | — | 99.6% |
| Wistfulness | GG | — | 64.9% | 71.1% | 76.7% | 81.6% | 85.7% |
| Wistfulness | UU | — | 78% | 82.9% | 87.1% | 90.5% | 93.1% |
| Wistfulness | 3GG | — | — | — | — | 94.6% | 95.2% |
| Wistfulness | 3UU | — | — | — | — | 98.8% | 99% |
| Wistfulness | 1GGUU | — | — | — | — | 93.4% | 94.2% |
| Emptiness | WW | — | 0% | 0% | 0% | 0% | 0% |
| Emptiness | BB | — | 81.8% | 86.1% | 89.7% | 92.6% | 94.8% |
| Emptiness | 4WW | — | — | — | — | — | 0% |
| Emptiness | 4BB | — | — | — | — | — | 99.9% |
| Emptiness | 2WWBB | — | — | — | — | — | 0% |
| Formidable Speaker | 2G | — | — | 96.9% | 97.5% | 98% | 98.5% |
| Bitter Triumph | 1B | — | 97.9% | 98.5% | 98.9% | 99.3% | 99.5% |
| Moonshadow | B | 94.1% | 96% | 97.4% | 98.3% | 98.9% | 99.3% |
| Awaken the Honored Dead | BGU | — | — | 95.4% | 96.3% | 97.1% | 97.8% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 96.1% | 96.8% | 97.4% |
| Sunderflock | 1UU | — | — | 89.7% | 91.7% | 93.5% | 95% |
| Sunderflock | UU | — | 78% | 82.9% | 87.1% | 90.5% | 93.1% |

## On the draw

| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---:|---:|---:|---:|---:|---:|
| Superior Spider-Man | 2UB | — | — | — | 99.7% | 99.8% | 99.8% |
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 97.8% | 98.2% | 98.6% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 96.7% | 97.3% | 97.9% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 94.8% | 95.8% | 96.7% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 96.7% | 97.3% | 97.9% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 89.8% | 91.3% | 92.8% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 97.8% | 98.2% | 98.6% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 0% | 0% | 0% |
| Deceit | UU | — | 82.9% | 87.1% | 90.5% | 93.1% | 95.2% |
| Deceit | BB | — | 86.1% | 89.7% | 92.6% | 94.8% | 96.4% |
| Deceit | 4UU | — | — | — | — | — | 99.7% |
| Deceit | 4BB | — | — | — | — | — | 99.9% |
| Deceit | 2UUBB | — | — | — | — | — | 99.7% |
| Wistfulness | GG | — | 71.1% | 76.7% | 81.6% | 85.7% | 89.1% |
| Wistfulness | UU | — | 82.9% | 87.1% | 90.5% | 93.1% | 95.2% |
| Wistfulness | 3GG | — | — | — | — | 95.2% | 95.9% |
| Wistfulness | 3UU | — | — | — | — | 99% | 99.1% |
| Wistfulness | 1GGUU | — | — | — | — | 94.2% | 95% |
| Emptiness | WW | — | 0% | 0% | 0% | 0% | 0% |
| Emptiness | BB | — | 86.1% | 89.7% | 92.6% | 94.8% | 96.4% |
| Emptiness | 4WW | — | — | — | — | — | 0% |
| Emptiness | 4BB | — | — | — | — | — | 99.9% |
| Emptiness | 2WWBB | — | — | — | — | — | 0% |
| Formidable Speaker | 2G | — | — | 97.5% | 98% | 98.5% | 98.8% |
| Bitter Triumph | 1B | — | 98.5% | 98.9% | 99.3% | 99.5% | 99.7% |
| Moonshadow | B | 96% | 97.4% | 98.3% | 98.9% | 99.3% | 99.6% |
| Awaken the Honored Dead | BGU | — | — | 96.3% | 97.1% | 97.8% | 98.4% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 96.8% | 97.4% | 97.9% |
| Sunderflock | 1UU | — | — | 91.7% | 93.5% | 95% | 96.3% |
| Sunderflock | UU | — | 82.9% | 87.1% | 90.5% | 93.1% | 95.2% |

## Mana-source inventory

| Land | Copies | Colors | Basic types | Condition |
|---|---:|---|---|---|
| Watery Grave | 11 | UB | UB |  |
| Overgrown Tomb | 8 | BG | BG |  |
| Breeding Pool | 7 | UG | UG |  |

Metadata and mathematical details: [analysis notes](../ideas/knowledge/mana-analysis.md).
