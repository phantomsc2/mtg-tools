# Mana optimum and per-card swap suggestions

Every deck contains exactly 60 cards: 26 lands and 34 nonlands. Suggestions replace lands only.
The explicit nonland scenario is compared separately below; the input deck file is unchanged.
Search is exhaustive within 59,109 bases: 1–2 Swamps, 0–1 Island, 0–1 Forest,
and 0–4 each Sultai shock, Sultai Verge, Starting Town and Cavern. No Sewers or Passage.
Penalty λ=2/625 (0.32 percentage points per shock or Town).
Fitness = normalized weighted color success − λ × (shocks + Towns); loss = 1 − fitness.

## Optimum

| Land | Copies |
|---|---:|
| Swamp | 2 |
| Overgrown Tomb | 4 |
| Watery Grave | 4 |
| Breeding Pool | 1 |
| Gloomlake Verge | 2 |
| Willowrush Verge | 4 |
| Starting Town | 4 |
| Cavern of Souls | 4 |
| Island | 1 |
| **Total lands** | **26** |

| Nonland | Copies | Importance |
|---|---:|---:|
| Superior Spider-Man | 4 | 1 |
| Deceit | 4 | 1 |
| Wistfulness | 4 | 1 |
| Formidable Speaker | 4 | 1 |
| Bitter Triumph | 4 | 1 |
| Moonshadow | 4 | 1 |
| Emptiness | 4 | 1 |
| Sunderflock | 4 | 1 |
| Awaken the Honored Dead | 2 | 1 |
| **Total nonlands** | **34** | |

Raw color success: **89.832821%**. Weighted success: **89.832821%**.
Penalty contribution: **4.160000%**. Regularized fitness: **85.672821%**; loss: **14.327179%**.
Co-optimal bases at current weights: 1; lexical counts select the printed base.

## Per-card sensitivity

Each direction varies only that card's importance, relative to its current value; other weights and λ stay fixed. Copy weights are renormalized; modes and play/draw stay uniform.
A threshold is an exact optimum crossing, not an iterated search over guessed coefficients.
**At the crossing, overall fitness improvement is zero.** The suggested base wins immediately beyond it.
Δcard is its change in conditional castability, averaged over modes/play/draw. Baseline cost is the overall fitness sacrificed under the original weights (both in percentage points).
Weights are renormalized while λ stays fixed. A weight change can therefore favor a different shock/Town tradeoff even when Δcard is zero or has the unexpected sign; the reported signed delta makes this explicit.
No arbitrary beyond-crossing probe contributes to the report. Endpoint ties at zero are not flips.
Simultaneous crossings choose the winning slope beyond the boundary, then minimum swaps, then lexical land counts. Identical lines do not manufacture flips.

| Card | Value less | Value more |
|---|---|---|
| Superior Spider-Man | No change through weight zero | Above ×27.152452<br>OUT: 1 Swamp, 1 Willowrush Verge<br>IN: 1 Breeding Pool, 1 Gloomlake Verge<br>Δcard +0.369059 pp; baseline cost +0.150944 pp |
| Deceit | Below ×0.475410<br>OUT: 1 Willowrush Verge<br>IN: 1 Breeding Pool<br>Δcard +0.003986 pp; baseline cost +0.019503 pp | Above ×2.963902<br>OUT: 1 Willowrush Verge<br>IN: 1 Gloomlake Verge<br>Δcard +0.293929 pp; baseline cost +0.067911 pp |
| Wistfulness | Below ×0.231327<br>OUT: 1 Willowrush Verge<br>IN: 1 Gloomlake Verge<br>Δcard -0.750965 pp; baseline cost +0.067911 pp | Above ×1.156560<br>OUT: 1 Island<br>IN: 1 Breeding Pool<br>Δcard +1.410456 pp; baseline cost +0.020085 pp |
| Formidable Speaker | Below ×0.260771<br>OUT: 1 Willowrush Verge, 1 Island<br>IN: 1 Breeding Pool, 1 Gloomlake Verge<br>Δcard +0.077419 pp; baseline cost +0.021097 pp | Above ×1.686991<br>OUT: 1 Gloomlake Verge<br>IN: 1 Wastewood Verge<br>Δcard +0.766254 pp; baseline cost +0.061931 pp |
| Bitter Triumph | Below ×0.466494<br>OUT: 1 Island<br>IN: 1 Breeding Pool<br>Δcard +0.000000 pp; baseline cost +0.020085 pp | Above ×1.710191<br>OUT: 2 Willowrush Verge, 1 Island<br>IN: 2 Breeding Pool, 1 Gloomlake Verge<br>Δcard +1.001954 pp; baseline cost +0.030242 pp |
| Moonshadow | Below ×0.598349<br>OUT: 2 Willowrush Verge, 1 Island<br>IN: 2 Breeding Pool, 1 Gloomlake Verge<br>Δcard +0.000000 pp; baseline cost +0.030242 pp | Above ×4.288507<br>OUT: 1 Breeding Pool<br>IN: 1 Wastewood Verge<br>Δcard +0.000000 pp; baseline cost +0.123803 pp |
| Emptiness | Below ×0.466494<br>OUT: 1 Island<br>IN: 1 Breeding Pool<br>Δcard +0.000000 pp; baseline cost +0.020085 pp | Above ×2.021412<br>OUT: 1 Willowrush Verge, 1 Island<br>IN: 1 Breeding Pool, 1 Gloomlake Verge<br>Δcard +0.495563 pp; baseline cost +0.021097 pp |
| Sunderflock | Below ×0.713357<br>OUT: 1 Willowrush Verge, 1 Island<br>IN: 1 Breeding Pool, 1 Wastewood Verge<br>Δcard -1.240451 pp; baseline cost +0.052623 pp | Above ×2.617670<br>OUT: 1 Swamp<br>IN: 1 Gloomlake Verge<br>Δcard +1.026636 pp; baseline cost +0.195383 pp |
| Awaken the Honored Dead | No change through weight zero | Above ×1.380483<br>OUT: 1 Willowrush Verge<br>IN: 1 Breeding Pool<br>Δcard +1.191406 pp; baseline cost +0.019503 pp |

## Awaken / Bitter Triumph replacement

| Spell | Original copies | Revised copies |
|---|---:|---:|
| Awaken the Honored Dead | 3 | 2 |
| Bitter Triumph | 3 | 4 |

| Land | Original-package optimum | Revised-package optimum |
|---|---:|---:|
| Swamp | 2 | 2 |
| Overgrown Tomb | 4 | 4 |
| Watery Grave | 4 | 4 |
| Breeding Pool | 2 | 1 |
| Gloomlake Verge | 2 | 2 |
| Willowrush Verge | 4 | 4 |
| Starting Town | 4 | 4 |
| Cavern of Souls | 4 | 4 |
| Island | 0 | 1 |

Combined 60-card change: OUT: 1 Awaken the Honored Dead, 1 Breeding Pool<br>IN: 1 Bitter Triumph, 1 Island.
Native scores below belong to different spell packages and are not a win-rate comparison.

| Evaluation | Weighted color success | Regularized fitness |
|---|---:|---:|
| Original package, its optimum | 89.696402% | 85.216402% |
| Revised package, original land base | 90.132736% | 85.652736% |
| Revised package, revised optimum | 89.832821% | 85.672821% |

Gain from adapting the lands, evaluated under the **same revised package**: **0.020085 percentage points**.

## Casting coverage of the revised optimum

Seven-card keeps; see T+6 cards on the play or T+7 on the draw. Each percentage conditions on
seeing the target and enough lands for that payment. Choose the best subset of up to T lands.
Ignore draw order, tapped entry, actual life payments, nonmana costs, targets, ramp, extra draws
and mulligans. Cavern casts every creature; Verge activation uses actual chosen basic types.
Single-effect rows include both-effect payments; rows overlap. Spider-Man copy targets and
Sunderflock discount enablers are assumed available, not established by a rollout.
The metric includes earliest turns beyond T6 (e.g. Sunderflock T8/T9), despite this table's range.
— means unavailable before the total cost's turn. Percentages have at most one decimal.

### On the play

| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---:|---:|---:|---:|---:|---:|
| Superior Spider-Man | 2UB | — | — | — | 99.9% | 99.9% | 99.9% |
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 98.1% | 98.5% | 98.8% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 98.5% | 98.8% | 99.1% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 96.8% | 97.4% | 97.9% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 98.5% | 98.8% | 99.1% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 90.6% | 92.1% | 93.5% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 98.1% | 98.5% | 98.8% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 43.1% | 46.9% | 51% |
| Deceit | UU | — | 85.2% | 89% | 92% | 94.4% | 96.2% |
| Deceit | BB | — | 81.9% | 87% | 90.5% | 93.3% | 95.4% |
| Deceit | 4UU | — | — | — | — | — | 100% |
| Deceit | 4BB | — | — | — | — | — | 100% |
| Deceit | 2UUBB | — | — | — | — | — | 99.9% |
| Wistfulness | GG | — | 61.5% | 74.2% | 79.9% | 84.8% | 88.7% |
| Wistfulness | UU | — | 85.2% | 89% | 92% | 94.4% | 96.2% |
| Wistfulness | 3GG | — | — | — | — | 97.4% | 97.7% |
| Wistfulness | 3UU | — | — | — | — | 99.7% | 99.8% |
| Wistfulness | 1GGUU | — | — | — | — | 96% | 96.6% |
| Emptiness | WW | — | 27.1% | 32.2% | 37.5% | 42.8% | 48.1% |
| Emptiness | BB | — | 81.9% | 87% | 90.5% | 93.3% | 95.4% |
| Emptiness | 4WW | — | — | — | — | — | 67.7% |
| Emptiness | 4BB | — | — | — | — | — | 100% |
| Emptiness | 2WWBB | — | — | — | — | — | 65% |
| Formidable Speaker | 2G | — | — | 97.7% | 98.2% | 98.6% | 99% |
| Bitter Triumph | 1B | — | 92.4% | 94.1% | 95.6% | 96.8% | 97.7% |
| Moonshadow | B | 92.7% | 95.5% | 97.1% | 98.1% | 98.8% | 99.3% |
| Awaken the Honored Dead | BGU | — | — | 74.7% | 79.3% | 83.4% | 87.1% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 98.6% | 98.9% | 99.1% |
| Sunderflock | 1UU | — | — | 94.7% | 95.9% | 96.9% | 97.7% |
| Sunderflock | UU | — | 85.2% | 89% | 92% | 94.4% | 96.2% |

### On the draw

| Card | Cost | T1 | T2 | T3 | T4 | T5 | T6 |
|---|---|---:|---:|---:|---:|---:|---:|
| Superior Spider-Man | 2UB | — | — | — | 99.9% | 99.9% | 99.9% |
| Superior Spider-Man → Deceit | 1BBU | — | — | — | 98.5% | 98.8% | 99.1% |
| Superior Spider-Man → Deceit | 1BUU | — | — | — | 98.8% | 99.1% | 99.3% |
| Superior Spider-Man → Deceit | BBUU | — | — | — | 97.4% | 97.9% | 98.4% |
| Superior Spider-Man → Wistfulness | 1BUU | — | — | — | 98.8% | 99.1% | 99.3% |
| Superior Spider-Man → Wistfulness | BUGG | — | — | — | 92.1% | 93.5% | 94.8% |
| Superior Spider-Man → Emptiness | 1BBU | — | — | — | 98.5% | 98.8% | 99.1% |
| Superior Spider-Man → Emptiness | BUWW | — | — | — | 46.9% | 51% | 55.1% |
| Deceit | UU | — | 89% | 92% | 94.4% | 96.2% | 97.4% |
| Deceit | BB | — | 86.2% | 90.5% | 93.3% | 95.4% | 96.9% |
| Deceit | 4UU | — | — | — | — | — | 100% |
| Deceit | 4BB | — | — | — | — | — | 100% |
| Deceit | 2UUBB | — | — | — | — | — | 99.9% |
| Wistfulness | GG | — | 67.7% | 79.9% | 84.8% | 88.7% | 91.8% |
| Wistfulness | UU | — | 89% | 92% | 94.4% | 96.2% | 97.4% |
| Wistfulness | 3GG | — | — | — | — | 97.7% | 98.1% |
| Wistfulness | 3UU | — | — | — | — | 99.8% | 99.8% |
| Wistfulness | 1GGUU | — | — | — | — | 96.6% | 97.2% |
| Emptiness | WW | — | 32.2% | 37.5% | 42.8% | 48.1% | 53.3% |
| Emptiness | BB | — | 86.2% | 90.5% | 93.3% | 95.4% | 96.9% |
| Emptiness | 4WW | — | — | — | — | — | 69.2% |
| Emptiness | 4BB | — | — | — | — | — | 100% |
| Emptiness | 2WWBB | — | — | — | — | — | 66.9% |
| Formidable Speaker | 2G | — | — | 98.2% | 98.6% | 99% | 99.3% |
| Bitter Triumph | 1B | — | 94.1% | 95.6% | 96.8% | 97.7% | 98.4% |
| Moonshadow | B | 95% | 97.1% | 98.1% | 98.8% | 99.3% | 99.6% |
| Awaken the Honored Dead | BGU | — | — | 79.3% | 83.4% | 87.1% | 90.1% |
| Sunderflock | 7UU | — | — | — | — | — | — |
| Sunderflock | 6UU | — | — | — | — | — | — |
| Sunderflock | 2UU | — | — | — | 98.9% | 99.1% | 99.3% |
| Sunderflock | 1UU | — | — | 95.9% | 96.9% | 97.7% | 98.4% |
| Sunderflock | UU | — | 89% | 92% | 94.4% | 96.2% | 97.4% |

All probabilities, crossings and score comparisons use exact rational/integer arithmetic.
Displayed values are rounded. JSON retains fractions, candidate compositions and successor intervals; CSV contains the sensitivity rows.
The companion .deck.txt exports the revised optimal 60-card deck.
