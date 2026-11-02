# Direct-metric card importance

`mana_fitness.mode_weights` accepts rational per-card multipliers. A weight
multiplies each physical copy's contribution; divide by total weighted copies.
Each card's modes remain uniform and play/draw are equally weighted. Default
weights of one reproduce the original normalization. For Awaken's three copies,
total weighted copies are 31+3w. The life-composition penalty remains lambda=.0032
on the normalized score scale. Drawing probabilities and the actual deck do not
change with importance weights.

`mana_card_weight_search.py` searches the same 59,109-base bounded neighborhood
(26 lands, at least one Swamp, caps 2 Swamp / 1 Island / 1 Forest, four-copy
nonbasics, no Passage). The basic evaluator exposes its exact per-requirement
components so this analysis reuses the existing binomial-grid machinery.

Let S be original success, A be Awaken's average conditional castability and K
the shock+Town count. Weighted success is

    [34*S + 3*(w-1)*A] / (31+3*w).

After subtracting lambda*K, clearing the positive common denominator gives
the linear objective

    (34*S - 3*A - 31*lambda*K) + w*(3*A - 3*lambda*K).

The first land-choice change is therefore the minimum exact crossing above
w=1 against the baseline-winning line, not a coarse sampled weight sweep.
Simultaneous crossings choose the largest slope for the right-hand successor.
Find its next crossing too, then select a simple decimal multiplier strictly
inside that first successor's interval. JSON retains exact threshold fractions.

The first threshold is w=1.098974706600 (rounded). Use w=1.10 (+10% Awaken
importance); the new optimum persists until w=1.129317364292. Replace one
Willowrush with one Island. Keep 2 Swamp, 4 Tomb, 4 Grave, 2 Pool, 2 Gloomlake,
3 Willowrush, 4 Town, 4 Cavern, 1 Island: ten shocks, three basics, 14 penalized
lands. Awaken's play/draw mean rises from 78.165731% to 78.468184%, whereas
the original unweighted score falls slightly from 89.696402% to 89.693761%.
The Island contributes its land type: both it and Willowrush already produce U.

Tests cover normalization, copy/mode/play-draw weights, exact old-weight
reduction, invalid weights, first line crossings, simultaneous crossings,
absent transitions, and choosing coefficients inside narrow intervals.
The four Awaken probabilities for before/after bases additionally agree with
the original scalar exact evaluator. All 32 tests pass, including JSON config
defaults and command-line precedence for the explicit weight option.

## Physical nonland replacement: two Awaken, four Bitter Triumph

At weight 1.0 and lambda=.0032, replacing one actual Awaken copy with a fourth
Bitter Triumph gives a unique optimum in the same 59,109-base bounded pool:
2 Swamp, 1 Island, 4 Tomb, 4 Grave, 1 Pool, 2 Gloomlake, 4 Willowrush,
4 Town, 4 Cavern. Relative to the original weight-1 optimum, replace Pool
with Island. Relative to the weight-1.10 original spell package, replace Pool
with Willowrush. This has nine shocks and three basics.

`evaluate_pool` now accepts an optional deck Counter (still 34 nonlands).
This recalculation uses target-copy counts 2 and 4 in the without-replacement
conditioning, not just changed objective weights. The resource deck file was
not modified. Exact fractions: reports/two-awaken-four-triumph.json.
