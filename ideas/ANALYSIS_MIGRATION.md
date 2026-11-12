# Raw-score analysis migration

The following obsolete experiments and result-dependent conclusions are retired as part of the raw-score refactor. Primary workflows and fixed-count raw comparisons are retained; their regenerated scores and winners may differ. Independent runtime/availability benchmark measurements remain historical measurements.

## Removal manifest

- examples/moonshadow_four_turn_penalty_sweep.py
- examples/moonshadow_four_turn_search.py
- examples/moonshadow_search.py
- examples/moonshadow_shock_targets.py
- examples/moonshadow_slow_search.py
- examples/moonshadow_ten_shock_fallback.py
- examples/user_fast_land_search.py
- reports/land_model_robustness.md
- reports/moonshadow_decay_h1_shock0.json
- reports/moonshadow_decay_h1_shock0.md
- reports/moonshadow_decay_h1_shock0.txt
- reports/moonshadow_four_turn_penalty_sweep.json
- reports/moonshadow_four_turn_search.json
- reports/moonshadow_h1_10shocks.json
- reports/moonshadow_h1_10shocks.txt
- reports/moonshadow_h1_8shocks.json
- reports/moonshadow_h1_8shocks.txt
- reports/moonshadow_h2_10shocks.json
- reports/moonshadow_h2_10shocks.txt
- reports/moonshadow_h2_12shocks.json
- reports/moonshadow_h2_12shocks.txt
- reports/moonshadow_h2_8shocks.json
- reports/moonshadow_h2_8shocks.txt
- reports/moonshadow_search.json
- reports/moonshadow_slow_search.json
- reports/no_cavern_optimization.json
- reports/no_cavern_optimization.md
- reports/robustness_experiment.py
- reports/robustness_results.json
- reports/user_fast_land_search.json

- reports/moonshadow_h2_landscape_progress.json (redundant interim checkpoint; final results retained)

## Documentation conclusions retired

- Penalty-based winner, crossing and robustness conclusions in the calculation notes.
- Penalty-envelope and winner interpretation sections in the retained fixed-count comparisons.

Fixed-count raw scores are retained with explicit provenance. Refreshed unconstrained reports are reoptimized; former selected bases are not relabeled as new winners.

## Validation and component reuse

Retained probability rows were reused only after checking the complete production-model signature, timing weights, source bounds, spell profiles and draw settings. Scores were recomputed with the new schema, and a fresh physical evaluation per half-life confirmed equality. No old adjusted scores were imported. Old serialized result/table schemas and cache signatures are rejected by the public API.

Both notebooks were executed in their kernels on reduced constrained spaces. Smoke-test outputs were cleared through the IDE, leaving full default source inputs and fresh kernels for the next run.
