"""Sample input from resources/decks/evoke_elementals.txt, not core defaults.

Choose one representative payment per physical spell: UU for Wistfulness,
BB for Deceit/Emptiness, and undiscounted 7UU for Sunderflock. There are no
copy scenarios, triggers, alternative payments, or gameplay assumptions.
The 26-land base is illustrative, using only the supported source kinds;
it does not reproduce the original deck's Caverns or conditional lands.

Run from the project root: python -m examples.sultai
"""

from mana_opportunities import ManaSource, SpellCost, evaluate

SPELLS = (
    SpellCost("2UB", 4),  # Superior Spider-Man
    SpellCost("BB", 8),   # Deceit and Emptiness
    SpellCost("UU", 4),   # Wistfulness
    SpellCost("2G", 4),   # Formidable Speaker
    SpellCost("1B", 3),   # Bitter Triumph
    SpellCost("B", 4),    # Moonshadow
    SpellCost("7UU", 4),  # Sunderflock
    SpellCost("BGU", 3),  # Awaken the Honored Dead
)

MANA_BASE = {
    ManaSource("U", "basic"): 4,
    ManaSource("B", "basic"): 4,
    ManaSource("G", "basic"): 2,
    ManaSource("UB", "dual"): 4,
    ManaSource("UG", "dual"): 4,
    ManaSource("BG", "dual"): 4,
    ManaSource("WUBRG", "rainbow"): 4,
}


if __name__ == "__main__":
    result = evaluate(MANA_BASE, SPELLS)
    print(f"Mean weighted opportunities: {result.raw_score:.6f}")
    print(f"Composition penalty: {result.penalty:.6f}")
    print(f"Score: {result.score:.6f}")
