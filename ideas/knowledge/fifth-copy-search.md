# Fifth-copy sensitivity

`mana_fifth_copy.py` exhausts 21,856 bases at 26 lands/fixed Swamp when Tomb,
Grave, Town and Cavern may have five copies; Pool and the three Verges remain
capped at four. Each independent experiment caps the other three tested lands
at four. The loss penalty remains 0.004 per shock or Starting Town; ten shocks
is a preference induced by that penalty, not a hard constraint.

All four fifth copies improve the regularized objective. Relative to the
previous winner, best one-card cuts are Gloomlake for Town, Grave and Cavern,
and Wastewood for Tomb. Each individually reoptimized winner additionally
replaces one Breeding Pool with Willowrush. Net loss improvements in percentage
points are 1.002908 (Town), 0.154481 (Tomb), 0.260642 (Grave), 0.772985 (Cavern).

Allowing all four fifth copies together selects 1 Swamp, 5 Tomb, 5 Grave,
1 Gloomlake, 4 Willowrush, 5 Town, 5 Cavern. Raw success 91.892427%, penalized
loss 14.107573%. Pool and Wastewood are absent. This keeps ten shocks despite
the added flexibility. It does not test sixth copies or relax other land caps.

The binomial-grid evaluator now accepts custom category capacities. It checks
int64 safety using the unrestricted grid's full card count. All 23 tests pass,
including scalar exact agreement for a five-copy capacity vector. Baseline
score reproduces the previous regularized optimum. Full fractions and ranks
are in `reports/fifth-copy-search.csv`.
