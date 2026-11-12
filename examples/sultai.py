"""Sample input from resources/decks/evoke_elementals.txt, not core defaults.

Incarnation payment modes share importance uniformly; physical cards count once.
Incarnation modes target one or both enters effects, not bare castability.
Spider-Man modes represent copying incarnations with colored-mana payoffs.
Sunderflock modes assume no Elemental, MV5, or MV6 on board, respectively.
These scenarios share importance uniformly; board presence is not simulated.
The current spell package has four Awaken and two Glarb; no Overlords.
The supplied 28-land list is reduced to a feasible 26-land starting base
by cutting one Gloomlake Verge and one Wastewood Verge. Basics are flexible;
four Caverns, four Towns and two Restless Cottages are fixed in the search.
Starting Town and Cavern are separate unrestricted rainbow categories; actual
Cavern restrictions remain outside this model. Shocks carry both land types.

Run from the project root: python -m examples.sultai
"""

from mtg_tools.mana.lands import ManaSource
from mtg_tools.mana.policy import heuristic_mana_model
from mtg_tools.mana.spells import CastingMode, Spell, SpellCost
from mtg_tools.mana.evaluation import evaluate

MANA_MODEL = heuristic_mana_model()

SPELLS = (
    Spell(4, tuple(CastingMode(c) for c in ("2UB", "1UUB", "1UBB", "UUBB"))),  # Superior Spider-Man
    Spell(4, tuple(CastingMode(c) for c in ("UU", "BB", "4UU", "4BB", "2UUBB"))),  # Deceit
    Spell(4, tuple(CastingMode(c) for c in ("WW", "BB", "4WW", "4BB", "2WWBB"))),  # Emptiness
    Spell(4, tuple(CastingMode(c) for c in ("UU", "GG", "3UU", "3GG", "1UUGG"))),  # Wistfulness
    SpellCost("2G", 4),   # Formidable Speaker
    SpellCost("1B", 2),   # Bitter Triumph
    Spell(4, tuple(CastingMode(c) for c in ("7UU", "2UU", "1UU"))),  # Sunderflock scenarios
    SpellCost("BGU", 4),  # Awaken the Honored Dead
    SpellCost("BGU", 2),  # Glarb, Calamity's Augur
    SpellCost("2BG", 2),  # Professor Dellian Fel
)

MANA_BASE = {
    ManaSource("B", "basic"): 1,
    ManaSource("U", "basic"): 1,
    ManaSource("BG", "tapped"): 2,
    ManaSource("UB", "shock", types="UB"): 3,
    ManaSource("UG", "shock", types="UG"): 4,
    ManaSource("BG", "shock", types="BG"): 2,
    ManaSource("WUBRG", "town"): 4,
    ManaSource("WUBRG", "cavern"): 4,
    ManaSource("UB", "verge"): 3,
    ManaSource("BG", "verge"): 1,
    ManaSource("UG", "verge"): 1,
}

LAND_NAMES = {
    ManaSource("BG", "tapped"): "Restless Cottage",
    ManaSource("B", "basic"): "Swamp",
    ManaSource("U", "basic"): "Island",
    ManaSource("G", "basic"): "Forest",
    ManaSource("UB", "shock", "UB"): "Watery Grave",
    ManaSource("UG", "shock", "UG"): "Breeding Pool",
    ManaSource("BG", "shock", "BG"): "Overgrown Tomb",
    ManaSource("WUBRG", "town"): "Starting Town",
    ManaSource("WUBRG", "cavern"): "Cavern of Souls",
    ManaSource("UB", "verge"): "Gloomlake Verge",
    ManaSource("BG", "verge"): "Wastewood Verge",
    ManaSource("UG", "verge"): "Willowrush Verge",
    ManaSource("UG", "fast"): "Botanical Sanctum",
    ManaSource("BG", "fast"): "Blooming Marsh",
    ManaSource("UBG", "tri"): "Opulent Palace",
}


if __name__ == "__main__":
    result = evaluate(MANA_BASE, SPELLS, model=MANA_MODEL)
    print(f"Score: {result.score:.6f}")
