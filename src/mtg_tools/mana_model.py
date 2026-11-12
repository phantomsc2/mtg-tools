"""Compatibility imports; implementation lives in mtg_tools.mana."""

from mtg_tools.mana.model import MODEL_VERSION as MODEL_VERSION
from mtg_tools.mana.model import CompiledManaModel as CompiledManaModel
from mtg_tools.mana.model import ManaContext as ManaContext
from mtg_tools.mana.model import ManaModel as ManaModel
from mtg_tools.mana.model import ManaOutcome as ManaOutcome
from mtg_tools.mana.model import _canonical as _canonical
from mtg_tools.mana.model import _probability as _probability
from mtg_tools.mana.model import type_mask as type_mask
from mtg_tools.mana.policy import heuristic_availability as heuristic_availability
from mtg_tools.mana.policy import heuristic_mana_model as heuristic_mana_model
from mtg_tools.mana.policy import turn_source_limit as turn_source_limit
