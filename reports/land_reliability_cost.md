# Runtime cost of land reliability

Historical measurements for the documented frozen workload; this report is not a current optimization recommendation.

## Reference and method

The batch component-table build uses `examples.sultai` with the existing reduced
reference-pool bounds: one fixed Swamp, 0-4 of each of three shocks, three Verges,
Town, and Cavern. This gives 26 lands, 3,144 candidates, nine source axes,
781,250 capacity-grid cells, and 18 canonical spell costs. Evaluation spans
turns 1-7, both play/draw positions, and opening size seven. No baseline is
passed into construction. Only Town has availability below one in this pool.

Compare the same current evaluator with land availability forced to one against
the current joint independent-availability model. This isolates the feature as
a whole, rather than the earlier separate-versus-joint comparison. Each timed
run uses a fresh Python process, with imports before the timer. Three unprofiled
runs per configuration alternate off/on/on/off/off/on. No other tests or builds
were run concurrently. Separate cProfile runs supply the breakdown.

Memory is the Windows process peak resident working set, read using
GetProcessMemoryInfo after construction; it includes Python, NumPy, imports,
and the resulting table. It is not a measurement of only array allocations.

## Unprofiled results

| Configuration | Times (s) | Median (s) | Median peak resident memory (MiB) |
| --- | --- | ---: | ---: |
| All lands available | 2.594, 2.667, 2.663 | 2.663 | 85.1 |
| Joint reliability | 9.148, 8.757, 8.786 | 8.786 | 141.4 |

Reliability makes this build 3.30x as slow, adding
6.12s (230% more runtime).
Peak resident memory rises by 56.3 MiB
(1.66x).
Local measurements do not predict all pools; additional unreliable source axes
and larger capacity grids can change the cost substantially. The large editable
notebook pool was not built.

## Profile breakdown

Cumulative times overlap and must not be added indiscriminately.

| Work | Reliability off | Joint reliability |
| --- | ---: | ---: |
| Full build | 2.521 s | 9.546 s |
| Weighted opportunity grids | bypassed | 4.246 s |
| Availability transforms, inside opportunity grids | bypassed | 2.923 s / 63 calls |
| Integer-limb binomial transforms | 1.811 s / 34 calls | 2.903 s / 46 calls |
| Candidate enumeration | 0.019 s | negligible |

The main added work is exact Python-integer grid arithmetic and averaging
availability along source axes. Extra denominator precision also increases
integer-limb transforms. Candidate enumeration and table-row assembly are small
relative to these grid calculations. The per-land rate formula itself is cheap.

Likely optimization targets are reducing repeated arbitrary-precision grid work,
sharing more intermediate availability transforms between costs, and tightening
or reducing common denominators before limb splitting. These are profiling-led
candidates, not changes implemented in this task.

## Reproduction artifacts

- `.cache/profile_reliability_total.py`: benchmark driver; run with the project
  Python and project dependencies on PYTHONPATH.
- `.cache/reliability_total.json`: individual timings and memory measurements.
- `.cache/reliability_off_profile.txt`, `.cache/reliability_on_profile.txt`:
  cumulative cProfile summaries.
- `.cache/reliability_off.prof`, `.cache/reliability_on.prof`: full profiles.
