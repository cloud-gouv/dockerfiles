"""Outscale : arrêt / démarrage des VMs workers via l'API du cloud.

Les VMs sont retrouvées à partir des Machines CAPI (spec.providerID). Une VM arrêtée
n'est plus facturée en calcul chez Outscale, d'où ce mode plutôt qu'une suppression.
Les identifiants OSC_ACCESS_KEY / OSC_SECRET_KEY / OSC_REGION sont lus par le SDK.
"""

import logging

from osc_sdk_python import Gateway
from requests.exceptions import HTTPError, RequestException

from .base import Change, PowerProvider, Target

log = logging.getLogger(__name__)

TARGET_STATE = {"stop": "stopped", "start": "running"}
API_ACTION = {"stop": "StopVms", "start": "StartVms"}
# Seul état depuis lequel l'API accepte l'action.
ACTIONABLE_STATE = {"stop": "running", "start": "stopped"}
# Action déjà en cours : rien à demander.
IN_PROGRESS_STATE = {"stop": "stopping", "start": "pending"}


class OutscaleProvider(PowerProvider):
    name = "outscale"
    default_poll_timeout_seconds = 300

    def __init__(self, capi, **common):
        super().__init__(capi, **common)
        self.gw = Gateway()

    def list_targets(self):
        targets = []
        for machine in self.capi.list_in_scope("machines"):
            machine_name = machine["metadata"]["name"]
            provider_id = machine.get("spec", {}).get("providerID")
            if not provider_id:
                log.warning("Machine %s sans providerID pour l'instant, ignorée", machine_name)
                continue
            vm_id = provider_id.rsplit("/", 1)[-1]
            # 'i-70807bed/cluster-md-0-abc12' : évite les parenthèses imbriquées dans les logs.
            targets.append(Target(name="{}/{}".format(vm_id, machine_name), ref=vm_id))
        return targets

    def plan(self, action, targets):
        desired = TARGET_STATE[action]
        states = self._read_states([t.ref for t in targets])
        changes = []
        for target in targets:
            state = states.get(target.ref)
            if state == desired:
                log.info("%s déjà %s, ignorée", target.name, desired)
                continue
            if state == IN_PROGRESS_STATE[action]:
                log.info("%s déjà en %s, ignorée", target.name, state)
                continue
            if state != ACTIONABLE_STATE[action]:
                # StartVms/StopVms part en un seul appel : une seule VM dans un état
                # incompatible (terminated, shutting-down...) fait refuser tout le lot en 409.
                log.warning("%s en état %s, impossible de la passer à %s : ignorée", target.name, state, desired)
                continue
            log.info("%s: %s -> %s", target.name, state, desired)
            changes.append(Change(target, desired))
        return changes

    def validate(self, action, changes):
        """Rejoue l'appel avec DryRun=true : l'API valide droits et paramètres sans rien modifier.

        Le SDK retire DryRun de la signature des méthodes générées, d'où le passage par
        gw.raw() qui envoie le payload tel quel. Quand la requête aurait abouti, l'API
        répond par une erreur DryRunOperation : c'est le cas nominal.
        """
        api_action = API_ACTION[action]
        try:
            result = self.gw.raw(api_action, DryRun=True, VmIds=self._vm_ids(changes))
        except HTTPError as exc:
            if "dryrunoperation" in str(exc).lower():
                log.info("[dry-run] %s validé par l'API (DryRunOperation)", api_action)
                return True
            log.error("[dry-run] %s refusé par l'API: %s", api_action, exc)
            return False

        errors = result.get("Errors") if isinstance(result, dict) else None
        if errors:
            if any("dryrun" in str(error.get("Type", "")).lower() for error in errors):
                log.info("[dry-run] %s validé par l'API (DryRunOperation)", api_action)
                return True
            log.error("[dry-run] %s refusé par l'API: %s", api_action, errors)
            return False

        log.info("[dry-run] %s validé par l'API: %s", api_action, result)
        return True

    def apply(self, action, changes):
        """Déclenche l'action sans se fier à sa réponse : c'est l'état lu ensuite qui fait foi.

        L'API peut traiter la demande puis laisser expirer la connexion (504) ; le retry
        du SDK repart alors sur des VMs déjà dans le bon état et échoue en 409
        InvalidVmState, alors que l'action a bien eu lieu. Plutôt que de trier les erreurs
        par code, on journalise et on laisse converged() trancher : si les VMs
        n'atteignent pas l'état visé, le timeout fera échouer le Job.
        """
        api_action = API_ACTION[action]
        try:
            getattr(self.gw, api_action)(VmIds=self._vm_ids(changes))
        except RequestException as exc:
            log.warning("%s en échec, vérification de l'état réel des VMs: %s", api_action, exc)
        return []

    def converged(self, changes):
        states = self._read_states(self._vm_ids(changes))
        return [c for c in changes if states.get(c.target.ref) == c.desired]

    @staticmethod
    def _vm_ids(changes):
        return [c.target.ref for c in changes]

    def _read_states(self, vm_ids):
        result = self.gw.ReadVms(Filters={"VmIds": vm_ids})
        return {vm["VmId"]: vm["State"] for vm in result.get("Vms", [])}
