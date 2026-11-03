"""Sample input from resources/decks/evoke_elementals.txt, not core defaults.

Incarnation payment modes share importance uniformly; physical cards count once.
Sunderflock remains undiscounted; copying and board scenarios are excluded.
The 26-land reference base fixes one Swamp and has no Island or Forest.
Starting Town and Cavern are separate unrestricted rainbow categories; actual
Cavern restrictions remain outside this model. Shocks carry both land types.

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
    ManaSource("B", "basic"): 1,
    ManaSource("UB", "shock", types="UB"): 4,
    ManaSource("UG", "shock", types="UG"): 4,
    ManaSource("BG", "shock", types="BG"): 4,
    ManaSource("WUBRG", "town"): 4,
    ManaSource("WUBRG", "cavern"): 4,
    ManaSource("UB", "verge"): 3,
    ManaSource("BG", "verge"): 1,
    ManaSource("UG", "verge"): 1,
}


if __name__ == "__main__":
    result = evaluate(MANA_BASE, SPELLS)
    print(f"Mean weighted opportunities: {result.raw_score:.6f}")
    print(f"Composition penalty: {result.penalty:.6f}")
    print(f"Score: {result.score:.6f}")
