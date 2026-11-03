"""Reference-pool exhaustive example: python -m examples.sultai_search."""

from time import perf_counter

from examples.sultai import MANA_BASE, SPELLS
from mana_search import ManaSpace, build_component_table


def main() -> None:
    space = ManaSpace({source: ((n, n) if source.kind == "basic" else (0, 4))
                       for source, n in MANA_BASE.items()}, land_count=26)
    print(f'Exhaustive pool: {space.candidate_count()} bases')
    start = perf_counter()
    table = build_component_table(space, SPELLS)
    print(f'Table built in {perf_counter() - start:.3f}s')
    start = perf_counter()
    scored = table.score(shock_penalty=0.01, town_penalty=0.01)
    ranked = scored.rank(limit=5, baseline=MANA_BASE)
    winner = dict(zip(space.sources, ranked[0].counts))
    print(f'Best score: {float(ranked[0].score):.6f}')
    print('Best base:', {f'{s.kind}:{s.colors}': n for s, n in winner.items() if n})
    for parameter in ('shock_penalty', 'town_penalty'):
        sensitivity = scored.crossings(parameter, baseline=winner)
        print(parameter, sensitivity.optimal_interval)
        for transition in (sensitivity.lower, sensitivity.upper):
            if transition is not None:
                print(f'Crossing at {transition.value}:', transition.swap)
    print(f'Report computed in {perf_counter() - start:.3f}s')


if __name__ == '__main__':
    main()
