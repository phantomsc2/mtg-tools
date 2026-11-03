# Joint independent-availability profile

Reference: `examples.sultai` spells and reference-pool bounds; 26 lands,
3,144 candidates, 9 source axes, 18 canonical costs, turns 1-7, both play/draw,
opening hand 7. Grid size: 781,250 cells (fixed-basic axis still has capacity 1).
Both runs use exact batch evaluation and include component-table assembly.
The before backend was copied before this change; inputs and integer-limb
safety rules are identical. No scalar fallback or hand sampling was used.

## Runtime

Two isolated unprofiled runs per backend, in joint/separate/separate/joint order.
Earlier exploratory runs overlapped tests and are excluded from these medians.

| Model | Runs (seconds) | Median (seconds) |
| --- | --- | --- |
| Separate factors | 11.526, 11.699 | 11.612 |
| Joint payment | 9.748, 11.508 | 10.628 |

The observed median is 8.5% lower for joint payment. Run-to-run
variation is visible; this is a local measurement, not a guaranteed speedup.
The notebook's much larger editable pool was not built.

## cProfile

Separate profile runs recorded the following cumulative times (overlapping
entries must not be added):

| Work | Before | After |
| --- | ---: | ---: |
| Full build | 11.626 s | 9.732 s |
| Weighted opportunity grids | 2.644 s | 4.356 s |
| Availability transforms (inside opportunity grids) | n/a | 3.015 s |
| Integer-limb binomial transforms | 4.704 s / 80 calls | 2.797 s / 46 calls |

Joint payment uses separable binomial thinning along source axes; only available
source counts feed the payment mask. It adds transform work, but uses tighter
axis-based denominators than the previous turn/max-draw scaling, reducing the
number of downstream limb transforms on this reference. The weighted grids
remain exact Python integers. This benchmark did not measure peak memory.

## Metric changes and checks

51,893 of 56,592 exact components decreased;
none increased. Best unpenalized score changed from
3.224521050 to 3.210794377.
All 63 tests pass, including physical draw/failure enumeration and scalar/batch
agreement. The unavailable-blue-source regression now scores zero on turn one.

Raw local artifacts: `.cache/availability_benchmark.json`,
`.cache/availability_separate_profile.txt`, `.cache/availability_joint_profile.txt`,
and the corresponding `.prof` files. The before backend and profiling script
are saved locally in `.cache/mana_batch_separate.py` and
`.cache/profile_joint_availability.py`.
