# Constant life-cost proxy

`mana_regularization.py` consumes the exact 3,144-base actual-pool ranking and
minimizes `1 - success + lambda * (shocks + Starting Towns)`. Lambda is in
normalized score units, not life points or expected life lost. Count penalty
weights shocks and Town identically; Cavern and Verges are unpenalized.

The exact upper envelope of success minus count penalty gives transitions:
12 shocks to 11 at lambda 0.0025977798170540895; 11 to 10 at
0.003489365100892422; 10 to 9 at 0.0045801292877384525. These decimal bounds
are rounded for documentation; comparisons use the original exact Fractions.
At each transition both adjacent bases tie. Four Towns and four Caverns are
retained throughout the nonnegative-penalty frontier in this restricted pool.

Default lambda 0.004 (0.4 percentage points per shock or Town) selects ten
shocks: 4 Tomb, 4 Grave, 2 Pool; 3 Gloomlake, 1 Wastewood, 3 Willowrush;
4 Town, 4 Cavern, 1 Swamp. Raw success 89.5878610246%, raw loss
10.4121389754%, penalized loss 16.0121389754%. Relative to the unregularized
winner, replace two Pools with two Willowrush; sacrifice 0.6087144918
percentage points of color success. This regularizer cannot represent draw
timing, whether a shock can enter tapped, or actual life payments.

All 22 tests pass, including exact penalty-envelope checks. CSV includes
every base's regularized score and fraction. The original deck is unchanged.
