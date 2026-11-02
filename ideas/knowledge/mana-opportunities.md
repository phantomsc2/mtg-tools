# Draw-based mana opportunities

`mana_opportunities.py` replaces the Sultai-specific analysis/search/report pipeline.
The core accepts cost counts with optional weights, and a supplied mana base.
`examples/sultai.py` is the sample cost profile; its illustrative lands replace the
original deck's unsupported conditional sources. The raw decklist is retained
only as sample data. Existing generic hand/search utilities remain independent.

Each drawn physical copy scores independently whenever its cost is payable.
Alternatives may use different land selections; neither spells nor mana are
consumed. This deliberately counts backups and ignores sequencing. Scores are
uniform means across T1 through T7 and both play/draw positions by default.
Do not interpret the result as win rate, casting throughput, or a probability.

For a cost with c copies, deck size D, N nonlands and s cards seen, its expected
payable copies are c times the sum over payable land vectors of
`product(comb(source_count, drawn_count)) * comb(N-1, s-land_count-1) / comb(D,s)`.
This marks each target copy in turn. It includes mana shortage in the denominator
and avoids enumerating joint spell hands. Zero-weight cards still affect draws.

Payment uses Hall's condition for all subsets of required colors. An integer DP
tracks land count and capped subset supplies, merging interchangeable sources.
Unconditional one-mana sources mean successful payment needs no battlefield search:
a matching plus enough generic sources fits within the turn's land-drop limit.
Payment weights are cached independently of importance and penalties.

Rainbow and dual penalties are independent coefficients per land in the base,
subtracted after averaging opportunities. Their scale is raw opportunities per
turn; old penalties on normalized conditional coverage are not transferable.

The module uses only the standard library. Tests compare against physical draws
and exhaustive mana assignments. Full repository tests require the neighboring
leitwerk checkout on PYTHONPATH if it is not installed in the test environment.
