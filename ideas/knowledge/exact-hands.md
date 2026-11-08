# Exact hand experiment

The original playout and fractional-count scripts were removed when introducing
the standalone mana-opportunity evaluator. They sampled with replacement, lost category
identity through frozenset caching, or used fractional finite-deck counts.

The entry point is experiment.py, with exact expectations in hands.py and discrete
integer search in search.py. The project uses uv for dependency management.

The illustrative hand score is not win probability. Large threats receive no
reward and reach their configured lower bound. Removal and discard are equivalent
to this scorer. Proposal limits and unique evaluation counts expose search progress.
