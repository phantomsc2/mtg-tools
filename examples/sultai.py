"""Sample input from resources/decks/evoke_elementals.txt, not core defaults.

Incarnation payment modes share importance uniformly; physical cards count once.
Sunderflock remains undiscounted; copying and board scenarios are excluded.
The 26-land base is illustrative, using only the supported source kinds;
it does not reproduce the original deck's Caverns or conditional lands.

Run from the project root: python -m examples.sultai
"""

from mana_opportunities import CastingMode, ManaSource, Spell, SpellCost, evaluate

SPELLS = (
    SpellCost("2UB", 4),  # Superior Spider-Man
    Spell(4, tuple(CastingMode(c) for c in ("UU", "BB", "4UU", "4BB", "2UUBB"))),  # Deceit
    Spell(4, tuple(CastingMode(c) for c in ("WW", "BB", "4WW", "4BB", "2WWBB"))),  # Emptiness
    Spell(4, tuple(CastingMode(c) for c in ("UU", "GG", "3UU", "3GG", "1UUGG"))),  # Wistfulness
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
