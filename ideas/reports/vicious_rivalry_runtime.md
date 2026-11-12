# Vicious Rivalry search runtime diagnosis

The run lasted approximately 168 minutes elapsed (21:06 to 23:54). Several workers ran concurrently, so the approximate worker durations below must not be added to obtain elapsed time.

| Half-life | UB start | BG start | UG start |
| --- | ---: | ---: | ---: |
| 1 | 21.4 min | 18.6 min | 32.8 min |
| 1.5 | about 61 min | about 57 min | about 66 min, interrupted |
| 2 | about 99 min | about 39 min | about 66 min, interrupted |

The h=1 timings are stored in its JSON report. The other durations are reconstructed from process start times, completed-start cache timestamps, and interruption time; they are approximate. There was also roughly 20 minutes of redundant sequential UG work after parallel UG workers were introduced. Total worker time was approximately eight hours, overlapping within the 168-minute elapsed run. No per-phase timer was recorded, so an exact one-swap versus two-swap runtime split cannot be recovered.

## Neighborhood expansion

| Saved base | One-swap neighbors | Neighbors within two swaps | Ratio |
| --- | ---: | ---: | ---: |
| h=1 | 52 | 916 | 17.6x |
| h=1.5 | 70 | 1,420 | 20.3x |
| h=2 | 63 | 1,295 | 20.6x |

The first one-land plateaus took roughly 390–550 distinct visits. The first completed h=1.5/h=2 starts each accumulated about 4,500 cached bases through multiple two-swap escapes and budget resumptions. This supports an approximate 80–90% of candidate work attributable to two-swap exploration, including the resulting additional descent/check cycles. This is an estimate, not a measured phase-time percentage. Pair candidates can also be more expensive than candidates on the initial descent.

The implementation checks pairs only at a one-land plateau, as intended. However, it scans the whole pair neighborhood for the best improvement, resumes one-land descent, then performs another pair check at the next plateau. Thus a search can pay for several full pair neighborhoods before its final certification.

## Bounded timing measurements

Measurements were taken after stopping the long searches, using the current code, h=2, the same Rivalry spell profiles, and clearing the land-weight cache before each sample. Eight evenly spaced candidates were sampled from each two-swap neighborhood. These are small deterministic samples, not exhaustive averages.

| Setup | Two-swap neighbors | Mean seconds per sampled evaluation |
| --- | ---: | ---: |
| Earlier eight-shock Moonshadow base/pool, no tapped slots | 1,085 | 0.638 |
| Earlier twelve-shock base/pool, no tapped slots | 1,185 | 0.560 |
| Rivalry base/pool, exactly two tapped slots | 1,295 | 1.265 |

The sampled old candidates had about 8–9 nonzero source categories; the new candidates had 10–12. More distinct production/availability groups increase the dynamic-programming state space. The three extra tapped choices and the exact-two constraint change both neighborhood structure and the bases visited; the extra pool dimensions alone do not explain the full slowdown.

Generating the earlier 1,085-neighbor set took 0.008 seconds. A profile of one new final-base evaluation attributed 0.708 of 0.812 profiled seconds (87%) to `_land_weights` in `mana_opportunities.py`: joint payment-distribution dynamic programming. This is the primary kernel to optimize, rather than neighborhood enumeration or score arithmetic.

For the same new final base, cold land-weight timings were 0.101 seconds at h=1/H=5, 0.232 at h=1.5/H=7, and 0.326 at h=2/H=9. Horizon cost is more than linear in this sample: a larger horizon also raises `max_lands` for the distribution computation. Exponential weighting arithmetic itself is cheap.

The new spell package did not increase evaluation cost in the controlled final-base comparison: old versus new spell profiles took 0.298/0.239 seconds on the old base and 0.381/0.331 on the new base. Vicious Rivalry shares the existing 2BG cost, and the profiles no longer include Moonshadow's B cost.

## Which changes mattered

- Default two-swap completion makes routine searches expensive, although the earlier comparison reports already used two swaps. The current case required more escapes and checks, not merely the existence of the feature.
- Tapped-land choices/exact totals, the shock cap, and the resulting more diverse candidate bases roughly doubled sampled per-candidate evaluation cost and modestly enlarged the final neighborhood.
- Half-life h=2 still uses nine turns, as before. Adding h=1.5 added another independent search; it did not change h=2's horizon.
- Penalty removal did not add work to the payment kernel. Search limits can change which bases are visited and how many local traps are encountered.
- The experiment's `complete_search` wrapper repeatedly doubled 2,000/4,000/8,000-visit budgets until certification. This defeated the practical runtime limit. The reusable `local_search` itself remained bounded.
- All three starts were independently taken through expensive completion checks. Cross-half-life caches were separate. Earlier reports benefited from warm caches: the old h=2 report took 626 seconds overall, but several later starts took only 1–17 seconds.
- Late parallelization duplicated some work. Checkpointing only after a completed start also lost the interrupted h=2 UG improvement's composition.

## Improvement priorities

1. Keep a firm total wall-clock/cold-evaluation budget; checkpoint every improvement and log per-phase seconds, cache misses/hits, and neighborhoods completed. Never silently double a requested budget.
2. Use first-improving two-swap escapes, then resume one-land descent immediately. Fully exhaust the pair neighborhood only when certifying that no improvement exists. This retains two-swap local-optimum certification while avoiding full scans of nonfinal plateaus, although the path and resulting optimum can change.
3. Run cheap one-land descent from multiple starts, then apply the expensive two-swap completion to the strongest few results. Reuse prior half-life winners as starts. Report how many starts actually completed.
4. Optimize `_land_weights`: reduce/canonicalize equivalent source groups and DP states, cache reusable kernels, and investigate turn-specific draw bounds. Preserve exact probabilities and verify equivalence against the current evaluator.
5. Reuse per-cost/per-turn payment probabilities across half-lives rather than recomputing them in isolated processes/caches. The turn weights differ, but the underlying casting probabilities for a fixed base and turn do not.

The analysis script now defaults to a fixed 500 visits per start and no automatic expansion. A visit includes cache hits, so a future runtime-oriented budget should distinguish visits from actual uncached evaluations.
