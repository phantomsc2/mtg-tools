# Exact hand experiment

The original scripts are historical references: the playout scripts sample with replacement,
the evolutionary cache loses category identity through frozenset, and the probability scripts
optimize fractional counts that do not define finite-deck hypergeometric probabilities.

The new entry point is experiment.py, with exact expectations in hands.py and integer searches
in search.py. The project uses uv with editable ../leitwerk, currently 0.9.0. Its Optimizer accepts
a mapping of Parameter leaves and supports sequential ask/tell with a constructor seed.

The default three-seed comparison reached 2.2196487313 with both algorithms, from baseline
2.1373394345. This is an illustrative hand score, not win probability. Large threats receive no
reward and reach their configured lower bound. Removal and discard are equivalent to this scorer.
Leitwerk can collapse onto repeated integer projections; proposal limits and actual unique
evaluation counts are essential for interpreting comparisons.
