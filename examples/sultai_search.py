"""Small bounded exhaustive and one-swap examples: python -m examples.sultai_search."""

from time import perf_counter

from examples.sultai import MANA_BASE, SPELLS
from mana_search import ManaSpace, build_component_table


def main() -> None:
    # A deliberately small neighborhood, not unrestricted mana-base search.
    space = ManaSpace({source: (count - 1, count + 1) for source, count in MANA_BASE.items()}, land_count=26)
    print(f"Bounded exhaustive pool: {space.candidate_count()} bases")
    for mode in ("exhaustive", "one_swap"):
        start = perf_counter()
        table = build_component_table(space, SPELLS, mode=mode, baseline=MANA_BASE)
        built = perf_counter() - start
        start = perf_counter()
        ranked = table.rank(dual_penalty=0.01, rainbow_penalty=0.02)
        # Vary absolute UU weight, using the current winner as reference.
        winner = dict(zip(space.sources, ranked[0].counts))
        sensitivity = table.crossings("UU", baseline=winner, dual_penalty=0.01, rainbow_penalty=0.02)
        print(f"\n{mode}: {len(table.rows)} bases, build {built:.3f}s, rank + crossings {perf_counter()-start:.3f}s")
        print(f"Best score within this candidate set: {float(ranked[0].score):.6f}")
        print("Best base:", {f"{s.kind}:{s.colors}": n for s, n in winner.items() if n})
        print("Starting-base score change:", f"{float(ranked[0].delta):+.6f}")
        print("Winner's absolute UU-weight interval:", sensitivity.optimal_interval)
        for direction, transition in (("lower", sensitivity.lower), ("higher", sensitivity.upper)):
            if transition is not None:
                print(f"Next winner at {direction} UU weight {transition.value}:", transition.swap)


if __name__ == "__main__":
    main()
