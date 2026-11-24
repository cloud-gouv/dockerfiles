"""Registre des providers : ajouter un cloud = un module ici + une ligne dans PROVIDERS."""

from .nubo import NuboProvider
from .outscale import OutscaleProvider

PROVIDERS = {cls.name: cls for cls in (NuboProvider, OutscaleProvider)}
