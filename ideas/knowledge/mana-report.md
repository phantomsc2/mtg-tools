# Bidirectional mana sensitivity report

`python mana_report.py --config mana-report.json` generates reports/mana-report
(.md, .json, .csv, .deck.txt). The configuration explicitly applies -1 Awaken,
+1 Bitter Triumph to the original 3/3 resource list. All importance weights
default to one; lambda=.0032. Never modify the source list or silently apply
the nonland replacement twice. Invalid 60-card totals, nonland counts other
than 34, land counts other than 26 and illegal nonbasic copy counts are errors.

The pool is unchanged: 59,109 bases with 1–2 Swamps, 0–1 Island, 0–1 Forest,
0–4 of each Sultai shock, Sultai Verge, Town and Cavern. No Sewers or Passage.
This is exhaustive within that pool, not an unrestricted-basic global optimum.

## Exact data reuse and crossing model

The pool evaluator accepts a shared in-memory requirement cache. Target copy
count is part of the key, so original and revised packages share unaffected
components but separately evaluate Awaken c=3/2 and Bitter Triumph c=3/4.
Per-card integer probability vectors average modes uniformly and play/draw
equally under a common exact denominator P. Baseline copy-importance masses
are integer m_c after clearing weight denominators; W=sum(m_c).

For candidate i, let R_i=sum(m_c*p_ic), K_i be its shock+Town count, and
lambda=l/q. Its current weighted success is R_i/(P*W). When one card's
weight is multiplied by x, rank using a_i + (x-1)*b_i, where

    a_i = q*R_i - l*P*W*K_i
    b_i = m_c*(q*p_ic - l*P*K_i).

Find the nearest exact intersections from x=1 in both directions. Downward
analysis is restricted to x>=0. Report a boundary-only zero tie separately,
not as a flip. At simultaneous intersections choose the slope winning beyond
the boundary, then the minimum number of replacements, then lexical counts.
Identical lines do not create spurious changes. Canonical current co-optima
use lexical counts, with immediate-direction ties explicitly marked.

Every reported crossing checks equality/global optimality at the boundary,
the original optimum halfway toward it, and successor optimality within its
first interval. These internal checks use rational/integer arithmetic, not
sampled searches. Swap quantities balance and preserve exactly 26 lands;
adding unchanged nonlands produces a validated 60-card deck.

## Score interpretation and outputs

At a crossing, overall gain is exactly zero. Do not invent a beyond-crossing
probe to display a positive improvement. Each less/more cell instead shows
the target card's castability delta and the overall fitness cost at baseline
weights, both in percentage points. The counterfactual becomes preferable
immediately beyond the stated threshold. JSON also stores absolute weights,
successor intervals and full candidate compositions.

The nonland scenario includes both native package optima and evaluates the
old mana base under the revised spell package, isolating land-adjustment gain
without conflating different spell packages' objectives. Original-package
Awaken sensitivity is retained as a regression reference.

The primary optimum's full T1–T6 tables keep the established one-decimal,
separate-play/draw format. Earliest-turn values reuse the search components;
later-turn scalar calculations share a cache across identical payment/copy
requirements. JSON retains exact table probabilities. Metric terms beyond T6
remain included even when those rows show all dashes in the coverage tables.

## Verification and interpretation

All 42 tests pass. The full generation reproduces the original 3/3 optimum,
the revised 2/4 optimum and the exact original Awaken crossing saved by the
previous single-card analysis (Willowrush to Island). All 18 directional
results have balanced swaps, valid 60-card resulting decks and nonnegative
baseline fitness costs. Selected revised-package Awaken, Bitter Triumph and
Spider-Man BUWW probabilities (both play/draw) match the scalar evaluator.
The combined package change is OUT one Awaken and one Breeding Pool, IN one
Bitter Triumph and one Island. Adapting the lands improves regularized fitness
by 0.020084938620452235 percentage points under the SAME revised package.

Important: normalizing importance weights while holding lambda fixed couples
the weight knob to the life-composition tradeoff. Some crossings can have zero
target-card castability improvement: e.g. increasing Moonshadow importance
eventually removes a penalized land without improving Moonshadow itself.
The slope is proportional to p_ic - lambda*K_i, not just p_ic. This is a
consequence of the approved normalized objective, not a crossing error; the
report shows signed target deltas and explains this explicitly.
