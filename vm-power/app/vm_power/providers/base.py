"""Contrat commun à tous les providers.

`PowerProvider.run()` porte le déroulé, identique quel que soit le cloud :

    list_targets()  ->  plan()  ->  validate() en dry-run
                                    apply() puis converged() en boucle sinon

Un provider n'implémente que ces cinq méthodes abstraites.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

ACTIONS = ("stop", "start")


@dataclass
class Target:
    """Un worker (ou groupe de workers) sur lequel le provider sait agir."""

    name: str  # libellé pour les logs, ex. 'i-70807bed/cluster-md-0-abc12'
    ref: Any  # ce dont le provider a besoin pour agir : id de VM, MachineDeployment...


@dataclass
class Change:
    """Une cible qui n'est pas dans l'état voulu, et l'état à atteindre."""

    target: Target
    desired: Any  # ex. 'stopped' pour Outscale, un nombre de replicas pour nubo

    @property
    def name(self):
        return self.target.name


class PowerProvider(ABC):
    #: Valeur de PROVIDER / --provider qui sélectionne cette classe.
    name = ""
    #: Durée d'attente de la convergence quand POLL_TIMEOUT_SECONDS n'est pas fixé.
    default_poll_timeout_seconds = 300

    def __init__(self, capi, dry_run=False, poll_interval_seconds=15, poll_timeout_seconds=None):
        self.capi = capi
        self.dry_run = dry_run
        self.poll_interval_seconds = poll_interval_seconds
        self.poll_timeout_seconds = poll_timeout_seconds or self.default_poll_timeout_seconds

    @classmethod
    def from_env(cls, capi, **common):
        """Construit le provider. À surcharger pour lire des variables d'environnement propres."""
        return cls(capi, **common)

    # --- à implémenter par chaque provider -------------------------------------------

    @abstractmethod
    def list_targets(self):
        """Cibles dans le périmètre (clusters exclus déjà filtrés) -> list[Target]."""

    @abstractmethod
    def plan(self, action, targets):
        """Cibles à modifier pour `action` -> list[Change]. Journalise celles déjà dans l'état voulu."""

    @abstractmethod
    def validate(self, action, changes):
        """Dry-run : fait valider les appels par l'API sans rien modifier -> bool."""

    @abstractmethod
    def apply(self, action, changes):
        """Déclenche les changements -> list[Change] des appels refusés."""

    @abstractmethod
    def converged(self, changes):
        """Lit l'état réel -> list[Change] ayant atteint `desired`."""

    # --- déroulé commun ----------------------------------------------------------------

    def run(self, action, wait=True):
        """Retourne True si tout a convergé (ou s'il n'y avait rien à faire)."""
        targets = self.list_targets()
        if not targets:
            log.info("aucune cible pour le cluster %s, rien à faire", self.capi.cluster_name)
            return True

        log.info(
            "provider=%s cluster=%s action=%s dry_run=%s cibles=%s",
            self.name,
            self.capi.cluster_name,
            action,
            self.dry_run,
            [t.name for t in targets],
        )

        changes = self.plan(action, targets)
        if not changes:
            log.info("rien à faire, toutes les cibles sont déjà dans l'état voulu")
            return True

        if self.dry_run:
            for change in changes:
                log.info("[dry-run] %s passerait à %s", change.name, change.desired)
            return self.validate(action, changes)

        failed = self.apply(action, changes)
        if failed:
            log.error("appel refusé sur: %s", sorted(c.name for c in failed))
        to_wait = [c for c in changes if c not in failed]

        if wait and to_wait:
            pending = self.wait_for(to_wait)
            if pending:
                log.error("toujours pas convergé après %ss: %s", self.poll_timeout_seconds, sorted(pending))
                return False

        if failed:
            return False
        log.info("action=%s terminée pour %s cible(s)", action, len(changes))
        return True

    def wait_for(self, changes):
        """Interroge converged() jusqu'au timeout. Retourne les noms qui n'ont pas convergé."""
        deadline = time.time() + self.poll_timeout_seconds
        pending = {c.name: c for c in changes}
        while pending and time.time() < deadline:
            time.sleep(self.poll_interval_seconds)
            for change in self.converged(list(pending.values())):
                log.info("%s a atteint l'état %s", change.name, change.desired)
                pending.pop(change.name, None)
        return pending
