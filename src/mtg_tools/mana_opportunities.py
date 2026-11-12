"""Compatibility imports; implementation lives in mtg_tools.mana."""

from mtg_tools.mana.evaluation import Opportunity as Opportunity
from mtg_tools.mana.evaluation import OpportunityResult as OpportunityResult
from mtg_tools.mana.evaluation import _land_weights as _land_weights
from mtg_tools.mana.evaluation import evaluate as evaluate
from mtg_tools.mana.spells import CastingMode as CastingMode
from mtg_tools.mana.spells import Spell as Spell
from mtg_tools.mana.spells import SpellCost as SpellCost
from mtg_tools.mana.spells import _count as _count
from mtg_tools.mana.spells import _parse_cost as _parse_cost
from mtg_tools.mana.spells import _weight as _weight
from mtg_tools.mana.spells import spell_components as spell_components
