# Exact mana-base search

`mana_search.py` exhausts all 3,144 bases with 26 lands, exactly one Swamp,
and counts 0–4 for Overgrown Tomb, Watery Grave, Breeding Pool, Gloomlake
Verge, Wastewood Verge, Willowrush Verge, Starting Town and Cavern of Souls.
The nonland package, mode list, sufficient-land conditioning and equal
play/draw weighting remain unchanged. This fixes the total number of lands;
the objective is not suitable for optimizing that number without revision.

For earliest-turn casting, feasible drawn land vectors are the upward closure
of payable vectors whose land count equals the cost. The closure can be
computed with boolean cumulative maxima along each category axis. Payable
vectors use Hall's condition over required colors, with actual Verge types.
A multidimensional binomial transform maps draw-vector values into event
weights for every possible deck capacity vector simultaneously. Multiplying
by the nonland draw factors before transforming retains exact conditioning
on seeing at least one target. Fixed 26-land, 34-nonland counts give common
conditioning denominators for each mode/play-draw component across decks.

The grid has shape (2,5,5,5,5,5,5,5,5), including drawn Swamp count. All
transform arithmetic is int64, with a bound checked against comb(67, seen)
because the unrestricted capacity grid has at most 33 lands plus 34 nonlands.
The resulting event weights fit int64; final rational aggregation uses Python
integers under an LCM denominator and is ranked without floating-point scores.
Floats are used only for display columns. Identical requirements can share
evaluations while retaining their separate mode weights.

The complete 19-test suite passes. Tests cover binomial transforms versus
direct sums, closure versus scalar payment checks, and exact probabilities
versus the existing scalar evaluator. Additional checks of the winning base
matched scalar event weights for BBUU, BUWW, 1GGUU and 7UU on the play.
Search regeneration takes about six seconds in the local isolated test runtime.

Winner: 1 Swamp, four of every shock, four Town, four Cavern, three Gloomlake,
one Wastewood, one Willowrush. Success 90.1965755164%; loss 9.8034244836%.
All top 50 bases maximize Town and Cavern; all top ten maximize all shocks.
This reflects free life payments, universal creature Caverns and uniform
weight for white modes. Do not interpret the ordering as actual win rate.
