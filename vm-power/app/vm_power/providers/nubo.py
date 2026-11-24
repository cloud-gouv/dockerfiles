"""nubo (OpenStack) : scale à 0 / restauration des MachineDeployment workers.

Sur nubo une instance arrêtée reste facturée : il faut la supprimer. On agit donc
uniquement sur les objets Kubernetes du cluster de management : passer une
MachineDeployment à `replicas: 0` fait supprimer les Machines par CAPI, et donc les
instances. Le nombre de replicas d'origine est sauvegardé dans une annotation avant la
mise à 0, et relu au start : aucune liste de tailles à maintenir à la main.

Les control planes ne sont jamais touchés (seules les MachineDeployment sont patchées),
donc l'API des clusters workload reste joignable la nuit.
"""

import logging

from kubernetes.client.rest import ApiException

from ..capi import describe
from ..settings import env_flag, env_int
from .base import Change, PowerProvider, Target

log = logging.getLogger(__name__)

MACHINE_DEPLOYMENTS = "machinedeployments"
MACHINES = "machines"
DEPLOYMENT_NAME_LABEL = "cluster.x-k8s.io/deployment-name"
SAVED_REPLICAS_ANNOTATION = "nubo-worker-scaler.dinum.gouv.fr/previous-replicas"
EXCLUDE_DRAIN_ANNOTATION = "machine.cluster.x-k8s.io/exclude-node-draining"
EXCLUDE_VOLUME_DETACH_ANNOTATION = "machine.cluster.x-k8s.io/exclude-wait-for-node-volume-detach"


class NuboProvider(PowerProvider):
    name = "nubo"
    default_poll_timeout_seconds = 900

    def __init__(self, capi, fallback_replicas=1, skip_node_drain=False, **common):
        super().__init__(capi, **common)
        # Replicas appliqués au start quand l'annotation manque (0 = ne rien faire).
        self.fallback_replicas = fallback_replicas
        # Supprime les Machines sans drain au stop : un PDB ne bloque plus la suppression.
        self.skip_node_drain = skip_node_drain

    @classmethod
    def from_env(cls, capi, **common):
        return cls(
            capi,
            fallback_replicas=env_int("FALLBACK_REPLICAS", 1),
            skip_node_drain=env_flag("SKIP_NODE_DRAIN"),
            **common,
        )

    def list_targets(self):
        return [Target(name=describe(md), ref=md) for md in self.capi.list_in_scope(MACHINE_DEPLOYMENTS)]

    def plan(self, action, targets):
        plan = self._plan_stop if action == "stop" else self._plan_start
        return [change for change in (plan(t) for t in targets) if change is not None]

    def validate(self, action, changes):
        return not self._patch_all(action, changes, dry_run=True)

    def apply(self, action, changes):
        return self._patch_all(action, changes, dry_run=False)

    def converged(self, changes):
        done = []
        for change in changes:
            meta = change.target.ref["metadata"]
            try:
                status = self.capi.get(meta["namespace"], MACHINE_DEPLOYMENTS, meta["name"]).get("status", {})
            except ApiException as exc:
                log.warning("lecture du statut de %s impossible: %s", change.name, exc)
                continue
            if change.desired == 0:
                reached = status.get("replicas", 0) == 0
            else:
                reached = status.get("readyReplicas", 0) >= change.desired
            if reached:
                done.append(change)
        return done

    # --- détails nubo ------------------------------------------------------------------

    def _plan_stop(self, target):
        replicas = target.ref.get("spec", {}).get("replicas", 0)
        if replicas == 0:
            # Ne surtout pas réécrire l'annotation ici : elle vaudrait 0 et le start
            # du matin remonterait le pool à zéro.
            log.info("%s déjà à 0 replica, ignorée", target.name)
            return None
        log.info("%s: %s -> 0 replica", target.name, replicas)
        return Change(target, 0)

    def _plan_start(self, target):
        replicas = target.ref.get("spec", {}).get("replicas", 0)
        previous = self._saved_replicas(target)

        if replicas != 0:
            if previous is None:
                log.info("%s déjà à %s replicas, ignorée", target.name, replicas)
            else:
                # Remontée à la main (ou par un helmfile apply) : l'annotation ne sert plus à rien.
                log.info("%s déjà à %s replicas, nettoyage de l'annotation", target.name, replicas)
                body = {"metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: None}}}
                try:
                    self._patch(target, body, self.dry_run)
                except ApiException as exc:
                    log.warning("nettoyage de l'annotation sur %s impossible: %s", target.name, exc)
            return None

        if previous is not None:
            log.info("%s: 0 -> %s replicas (annotation)", target.name, previous)
            return Change(target, previous)

        if self.fallback_replicas <= 0:
            log.warning(
                "%s est à 0 sans annotation %s et FALLBACK_REPLICAS=0, laissée telle quelle",
                target.name,
                SAVED_REPLICAS_ANNOTATION,
            )
            return None
        # Un pool volontairement à 0 et jamais éteint par cet outil remonterait donc
        # à FALLBACK_REPLICAS : mettre FALLBACK_REPLICAS=0 pour l'éviter.
        log.warning("%s est à 0 sans annotation, remontée au fallback %s replicas", target.name, self.fallback_replicas)
        return Change(target, self.fallback_replicas)

    def _patch_all(self, action, changes, dry_run):
        failed = []
        for change in changes:
            if action == "stop":
                current = change.target.ref.get("spec", {}).get("replicas", 0)
                body = {
                    "metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: str(current)}},
                    "spec": {"replicas": 0},
                }
                if self.skip_node_drain:
                    self._skip_drain(change.target, dry_run)
            else:
                body = {
                    "metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: None}},
                    "spec": {"replicas": change.desired},
                }
            try:
                self._patch(change.target, body, dry_run)
            except ApiException as exc:
                log.error("patch de %s refusé: %s", change.name, exc)
                failed.append(change)
                continue
            if dry_run:
                log.info("[dry-run] %s validé par l'API (dryRun=All)", change.name)
        return failed

    def _skip_drain(self, target, dry_run):
        """Pose exclude-node-draining et exclude-wait-for-node-volume-detach sur les Machines.

        CAPI ne les lit que sur la Machine. Pas de nettoyage au start : ces Machines sont
        supprimées, celles recréées le matin naissent sans les annotations.
        Pas bloquant en cas d'échec : CAPI fera un drain classique, au risque d'un PDB.
        """
        meta = target.ref["metadata"]
        body = {"metadata": {"annotations": {EXCLUDE_DRAIN_ANNOTATION: "", EXCLUDE_VOLUME_DETACH_ANNOTATION: ""}}}
        try:
            machines = self.capi.list_namespaced(
                meta["namespace"], MACHINES, "{}={}".format(DEPLOYMENT_NAME_LABEL, meta["name"])
            )
            for machine in machines:
                self.capi.patch(meta["namespace"], MACHINES, machine["metadata"]["name"], body, dry_run)
        except ApiException as exc:
            log.warning("annotations exclude-* impossibles sur les Machines de %s: %s", target.name, exc)
            return
        log.info("%s: drain et attente des volumes désactivés sur %s Machine(s)", target.name, len(machines))

    def _patch(self, target, body, dry_run):
        meta = target.ref["metadata"]
        self.capi.patch(meta["namespace"], MACHINE_DEPLOYMENTS, meta["name"], body, dry_run)

    @staticmethod
    def _saved_replicas(target):
        annotations = target.ref["metadata"].get("annotations") or {}
        raw = annotations.get(SAVED_REPLICAS_ANNOTATION)
        if raw is None:
            return None
        try:
            return int(raw)
        except ValueError:
            log.warning("annotation %s illisible sur %s: %r", SAVED_REPLICAS_ANNOTATION, target.name, raw)
            return None
