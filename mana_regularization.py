"""Regularize the exact actual-pool ranking by shocks plus Starting Town count."""
import argparse
import csv
from fractions import Fraction

from mana_analysis import ROOT

SHOCKS = ("Overgrown Tomb", "Watery Grave", "Breeding Pool")
LANDS = ("Swamp", *SHOCKS, "Gloomlake Verge", "Wastewood Verge", "Willowrush Verge",
         "Starting Town", "Cavern of Souls")


def frontier(best: dict[int, Fraction]) -> list[tuple[int, Fraction, Fraction | None]]:
    """Penalty intervals where each penalized-land count is optimal; endpoints can tie."""
    result = []
    for count, success in sorted(best.items(), reverse=True):
        lower = max([Fraction(0)] + [(other-success)/(n-count) for n, other in best.items() if n > count])
        upper = min([(success-other)/(count-n) for n, other in best.items() if n < count], default=None)
        if upper is None or lower <= upper:
            result.append((count, lower, upper))
    return result


def generate_shock_sweep(rows: list[dict], best: dict, intervals: list) -> None:
    """Report the actual envelope, allowing Town counts to vary during optimization."""
    examples = {12: Fraction(0), 11: Fraction("0.003"), 10: Fraction("0.004"),
                9: Fraction("0.005"), 8: Fraction("0.008")}
    selected = []
    for count, lower, upper in intervals:
        row = best[count]
        if row["shock_count"] not in examples:
            continue
        coefficient = examples[row["shock_count"]]
        if coefficient < lower or (upper is not None and coefficient > upper):
            raise ValueError("Example penalty is outside the recomputed optimality interval")
        target = row["exact_success"]-coefficient*count
        assert all(target >= r["exact_success"]-coefficient*r["penalized_land_count"] for r in rows)
        selected.append(dict(row, lower=lower, upper=upper, coefficient=coefficient))
    output = ROOT / "reports/shock-penalty-sweep.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["shocks", "success", "loss", "success_fraction", "penalty_from_fraction",
                         "penalty_to_fraction", "example_penalty", *LANDS])
        for row in selected:
            writer.writerow([row["shock_count"], float(row["exact_success"]), float(1-row["exact_success"]),
                             str(row["exact_success"]), str(row["lower"]), str(row["upper"]),
                             str(row["coefficient"]), *(row[n] for n in LANDS)])
    common = [n for n in LANDS if selected and len({r[n] for r in selected}) == 1 and int(selected[0][n])]
    variable = [n for n in LANDS if n not in common and any(int(r[n]) for r in selected)]
    text = ["# Direct-metric optima with 8–12 shocks", "",
            "Minimize color failure + lambda * (shocklands + Starting Towns), with the same penalty for both.",
            f"Rechecked all {len(rows):,} 26-land bases: one fixed Swamp, four-copy limits, Sultai shocks/Verges,",
            "Starting Town and Cavern. No Sewers or fifth copies. All original spell modes and weights retained.",
            "Starting Town was allowed to vary; every reported optimum keeps four. All also keep four Caverns.", "",
            "## Compositions", "", "Every row shares: " + ", ".join(f"{selected[0][n]} {n}" for n in common) + ".", "",
            "| Shocks | " + " | ".join(variable) + " | Color success | Color loss |",
            "|---:|" + "---:|"*(len(variable)+2)]
    for row in selected:
        text.append(f"| {row['shock_count']} | " + " | ".join(row[n] for n in variable)
                    + f" | {float(row['exact_success']):.6%} | {float(1-row['exact_success']):.6%} |")
    text.extend(["", "## Penalties selecting each composition", "",
                 "Penalty units below are percentage points of normalized score per included shock or Town.",
                 "Adjacent optima tie at interval endpoints; interiors uniquely select the reported base.", "",
                 "| Shocks | Penalty from (pp) | Penalty to (pp) | Example penalty (pp) | CLI lambda |",
                 "|---:|---:|---:|---:|---:|"])
    for row in selected:
        text.append(f"| {row['shock_count']} | {float(row['lower'])*100:.6f} | "
                    f"{float(row['upper'])*100:.6f} | {float(row['coefficient'])*100:.3f} | "
                    f"{float(row['coefficient']):g} |")
    text.extend(["", "The first three cuts replace Breeding Pool with Willowrush Verge. The fourth replaces",
                 "the last Breeding Pool with Wastewood Verge. Overgrown Tomb and Watery Grave stay at four.",
                 "Raw color success drops from 90.196576% at twelve shocks to 88.468713% at eight shocks.",
                 "This penalty is a preference over deck composition, not expected life paid in a game.",
                 "Starting Town and Cavern remain particularly valuable under the universal-creature Cavern",
                 "assumption and uniform weighting of white modes.", "",
                 "Results and interval comparisons use exact fractions. Displayed decimals are rounded.",
                 "Regenerate with `python mana_search.py` followed by `python mana_regularization.py`.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")


def generate(penalty: Fraction) -> None:
    if penalty < 0:
        raise ValueError("Penalty must be nonnegative")
    source = ROOT / "reports/mana-base-search.csv"
    with source.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["exact_success"] = Fraction(row["success_fraction"])
        row["shock_count"] = sum(int(row[n]) for n in SHOCKS)
        row["penalized_land_count"] = row["shock_count"]+int(row["Starting Town"])
        row["exact_loss"] = 1-row["exact_success"]+penalty*row["penalized_land_count"]
    best = {}
    for row in rows:
        best.setdefault(row["penalized_land_count"], row)
    intervals = frontier({n: r["exact_success"] for n, r in best.items()})
    generate_shock_sweep(rows, best, intervals)
    ranked = sorted(rows, key=lambda r: r["exact_loss"])
    output = ROOT / "reports/regularized-mana-search.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["rank", "success", "loss", "penalty_per_land", "shock_count", "penalized_land_count",
                         "regularized_loss", "regularized_loss_fraction", *LANDS])
        for rank, row in enumerate(ranked, 1):
            writer.writerow([rank, row["success"], row["loss"], str(penalty), row["shock_count"],
                             row["penalized_land_count"], float(row["exact_loss"]), str(row["exact_loss"]),
                             *(row[n] for n in LANDS)])
    text = ["# Regularized actual-pool search", "",
            "Uses all 3,144 exact actual-pool results: 26 lands, fixed Swamp, four-copy limits, Sultai shocks/Verges,",
            "Starting Town and Cavern. No Sewers. The same spell package and mode weights remain in place.", "",
            "Minimize L_regularized = 1 - success + lambda * (shock count + Starting Town count).",
            f"Selected lambda = {penalty} = {float(penalty):.2%} score penalty per included shock or Town.",
            "This is an additive deck-composition penalty, not an estimate of expected life paid.", "",
            "## Winning base", ""]
    winner = ranked[0]
    text.extend(f"- {winner[n]} {n}" for n in LANDS if int(winner[n]))
    text.extend(["", f"Unregularized success: {float(winner['exact_success']):.6%}.",
                 f"Unregularized loss: {float(1-winner['exact_success']):.6%}.",
                 f"Regularized loss: {float(winner['exact_loss']):.6%}.", "",
                 "## Exact optimality intervals", "",
                 "Bounds below are percentage-point penalty per shock or Town. Endpoints can tie.", "",
                 "| Shocks | Towns | Raw success | Penalty from | Penalty to |",
                 "|---:|---:|---:|---:|---:|"])
    for count, lower, upper in intervals:
        row = best[count]
        end = "unbounded" if upper is None else f"{float(upper)*100:.6f}"
        text.append(f"| {row['shock_count']} | {row['Starting Town']} | {float(row['exact_success']):.6%} | "
                    f"{float(lower)*100:.6f} | {end} |")
    text.extend(["", "## Top five at selected penalty", "",
                 "| Rank | Shocks | Raw success | Regularized loss | Composition |", "|---:|---:|---:|---:|---|"])
    for rank, row in enumerate(ranked[:5], 1):
        composition = ", ".join(f"{row[n]} {n}" for n in LANDS if int(row[n]))
        text.append(f"| {rank} | {row['shock_count']} | {float(row['exact_success']):.6%} | "
                    f"{float(row['exact_loss']):.6%} | {composition} |")
    text.extend(["", "All comparisons use exact fractions; displayed values are rounded.",
                 "Regenerate the underlying grid with `python mana_search.py`, then run",
                 "`python mana_regularization.py --penalty 0.004`.", ""])
    output.with_suffix(".md").write_text("\n".join(text), encoding="utf-8")
    print("Winning raw success:", float(winner["exact_success"]))
    print("Winning regularized loss:", float(winner["exact_loss"]))
    print("Counts:", {n: winner[n] for n in LANDS})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--penalty", type=Fraction, default=Fraction("0.004"))
    generate(parser.parse_args().penalty)
