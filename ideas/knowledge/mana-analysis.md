# Exact mana analysis

Run `python mana_analysis.py` to generate `reports/sultai-mana.md` and `.csv`.
The calculation uses only Python's standard library; card metadata is local in
`mana_analysis.py`. `--deck` and `--output` override the input and output stem.
The deck parser stops at Sideboard and rejects unrecognized main-deck lines.

## Probability

For land-category capacities n_i, drawn counts k_i, N nonlands, c target copies,
and s cards seen, each land vector has conditioning weight

    product(comb(n_i, k_i)) * [comb(N, s-sum(k_i)) - comb(N-c, s-sum(k_i))].

Out-of-range combinations contribute zero. Sum these weights over vectors with
at least m lands, and divide the successful weight by that sum. The common
`comb(deck_size, s)` factor cancels. This conditions on at least one target copy,
not on a reserved copy. All arithmetic is integer or Fraction until display.
Zero conditioning weight yields N/A rather than zero probability.

On each turn T, choose up to T of the lands seen, with m the mode's total cost.
The original earliest-turn view used T=m; the report now evaluates T1 through T6
separately in play and draw tables. Costs above T are marked unavailable.
Generic mana uses any remaining chosen source, including colorless Cavern.
Unused lands can supply the basic types needed to activate Verges. Choosing
min(T, lands seen) lands is sufficient because adding a land never hurts here.
All lands in this deck produce one mana. Conditional Verge colors depend only
on basic land types of the chosen battlefield, including lands tapped for mana.
For each chosen battlefield, Hall's condition over every subset of required
colors decides whether distinct lands can supply all colored pips. This handles
overlapping dual/rainbow sources without double-counting a source.

The calculation ignores all draw/land-drop order. It does not model previous
spells, nonmana costs, useful targets, opponent interaction, or life availability.
Single-effect rows mean at least that effect, so overlap with both-effect rows.
Mixed hybrid payments giving neither effect are deliberately excluded under the
agreed five-row convention. No probability of drawing/establishing a Sunderflock
enabler is included: discount rows are hypothetical board scenarios evaluated
on each turn that can pay the reduced cost. In particular UU on T2 is a color diagnostic,
not a claim that a prior nine-mana Elemental can be deployed by then without ramp.
Native Elemental mana values present are 1, 5, 6, and 9; copies made by Superior
Spider-Man do not introduce another value. Discount 9 bottoms out at UU.

## Metadata sources (checked 2026-11-02)

- [ECL official release notes](https://media.wizards.com/2026/downloads/ECL_Release_Notes_06HVqa76yI/AIuLLXK62r_EN_MTGECL_ReleaseNotes_20260106.pdf): incarnation costs, mana-spent triggers, Sunderflock reduction.
- [SPM official release notes](https://media.wizards.com/2025/downloads/SPM_Release_Notes_Dl1UJsBTRE/EN_MTGSPM_ReleaseNotes_gwdWVhPlTi.pdf): Superior Spider-Man.
- [TDM official release notes](https://media.wizards.com/2025/downloads/TDM_Release_Notes_YchagR1EZF/EN_MTGTDM_ReleaseNotes_20250107.pdf): Awaken the Honored Dead.
- [FIN official release notes](https://media.wizards.com/2025/downloads/FIN_Release_Notes_3O87RLY5EO/EN_FIN_Release_Notes_2025_1_15.pdf): Starting Town.
- Supplementary card records: [Moonshadow](https://mtg.wtf/card/ecl/313/Moonshadow), [Formidable Speaker](https://themanagrove.com/cards/formidable-speaker), [Bitter Triumph](https://mtg.wtf/card/soa/91/Bitter-Triumph), [Gloomlake Verge](https://mtg.wtf/card/dsk/331/Gloomlake-Verge), [Wastewood Verge](https://mtg.wtf/card/dft/505/Wastewood-Verge), [Willowrush Verge](https://ww-w.mtg.wtf/card/pdft/270p/Willowrush-Verge). Use deck names rather than collector numbers as identifiers.

## Validation

`python -m unittest -v` includes physical-card enumeration checks of integer
weights and conditional probabilities, exhaustive mana-assignment comparisons,
Verge/Cavern restrictions, and mode coverage. The existing float hand API remains
unchanged; `hands.hand_weights` exposes integer weights for exact consumers.

All 16 tests passed with Python 3.12.13, using the neighboring leitwerk checkout
on PYTHONPATH and its numpy/scipy dependencies in an isolated test environment.
The pre-existing `.venv` points at a removed Python executable; a local ignored
`.python` runtime and `.cache/test-env` were used without replacing it.
The generated CSV is additionally checked for probability bounds and agreement
between reduced fractions and raw integer event weights.

## Spider-Man copying Elementals

Added seven four-mana payment rows: Deceit 1BBU, 1BUU and BBUU;
Wistfulness 1BUU and BUGG; Emptiness 1BBU and BUWW. Every payment must
still cover Spider-Man's printed UB. The copied incarnation's mana-spent
triggers see the colors actually spent on Spider-Man. Single-effect rows
remain inclusive. Both Wistfulness effects would require UUGG plus B, and
both Emptiness effects WWBB plus U: neither fits four mana without a cost
increase, which this analysis excludes. Copying Moonshadow or Sunderflock
has the same color requirement as ordinary Spider-Man, so uses that row.

Copy scenarios assume the named creature already exists in a graveyard.
Their distribution conditions only on Spider-Man drawn and four lands seen;
it does not condition on drawing, discarding, or otherwise placing the copy
target. Cavern is evaluated while casting Spider-Man under the existing
all-creatures assumption. The official SPM notes linked above confirm that
the copied creature's enters abilities work.

The Markdown output has two tables (on the play / on the draw), with Card,
Cost and T1–T6 columns. Spider-Man copy targets are retained in Card labels;
mode and scenario columns are omitted. Each percentage has at most one decimal.
The CSV retains one row per casting requirement per turn with exact fractions
and event weights. Unavailable turn/cost combinations have empty fractions.
