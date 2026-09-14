import argparse
import logging
import os
import sys
import time

from kubernetes import client, config
from osc_sdk_python import Gateway
from requests.exceptions import HTTPError, RequestException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

TARGET_STATE = {"stop": "stopped", "start": "running"}
API_ACTION = {"stop": "StopVms", "start": "StartVms"}
POLL_INTERVAL_SECONDS = 15
POLL_TIMEOUT_SECONDS = 300
MACHINE_GROUP = "cluster.x-k8s.io"
MACHINE_PLURAL = "machines"
CLUSTER_NAME_LABEL = "cluster.x-k8s.io/cluster-name"
EXCLUDED_CLUSTER_SUBSTRINGS = [
    s.strip() for s in os.environ.get("EXCLUDED_CLUSTER_SUBSTRINGS", "mgmt").split(",") if s.strip()
]


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def get_worker_machines():
    """Retourne {vm_id: nom de la Machine}, dans l'ordre renvoyé par l'API Kubernetes."""
    config.load_incluster_config()
    api = client.CustomObjectsApi()
    machine_version = os.environ.get("CAPI_MACHINE_API_VERSION", "v1beta1")
    machines = api.list_cluster_custom_object(MACHINE_GROUP, machine_version, MACHINE_PLURAL)["items"]

    machine_names = {}
    for machine in machines:
        name = machine["metadata"]["name"]
        labels = machine["metadata"].get("labels", {})
        cluster_name = labels.get(CLUSTER_NAME_LABEL, "")
        if any(substring in cluster_name for substring in EXCLUDED_CLUSTER_SUBSTRINGS):
            log.info("skipping machine %s from excluded cluster %s", name, cluster_name)
            continue

        provider_id = machine.get("spec", {}).get("providerID")
        if not provider_id:
            log.warning("machine %s has no providerID yet, skipping", name)
            continue

        machine_names[provider_id.rsplit("/", 1)[-1]] = name

    if not machine_names:
        log.info("no VM found via '%s/%s %s', nothing to do", MACHINE_GROUP, machine_version, MACHINE_PLURAL)
    return machine_names


def describe(vm_id, machine_names):
    """'i-70807bed/cluster-md-0-abc12' — évite les parenthèses imbriquées dans les logs."""
    return "{}/{}".format(vm_id, machine_names.get(vm_id, "unknown-machine"))


def wait_for_state(gw, vm_ids, target_state, machine_names):
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    pending = set(vm_ids)
    while pending and time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        result = gw.ReadVms(Filters={"VmIds": list(pending)})
        for vm in result.get("Vms", []):
            if vm["State"] == target_state:
                log.info("%s reached state %s", describe(vm["VmId"], machine_names), target_state)
                pending.discard(vm["VmId"])
    return pending


def request_power_change(gw, action, vm_ids):
    """Déclenche l'action sans se fier à sa réponse : c'est l'état lu ensuite qui fait foi.

    L'API peut traiter la demande puis laisser expirer la connexion (504) ; le retry
    du SDK repart alors sur des VMs déjà dans le bon état et échoue en 409
    InvalidVmState, alors que l'action a bien eu lieu. Plutôt que de trier les erreurs
    par code, on journalise et on laisse wait_for_state trancher : si les VMs
    n'atteignent pas l'état visé, le timeout fera échouer le Job.
    """
    try:
        getattr(gw, API_ACTION[action])(VmIds=vm_ids)
    except RequestException as exc:
        log.warning("%s failed, checking the actual VM state instead: %s", API_ACTION[action], exc)


def get_current_states(gw, vm_ids):
    result = gw.ReadVms(Filters={"VmIds": vm_ids})
    return {vm["VmId"]: vm["State"] for vm in result.get("Vms", [])}


def api_dry_run(gw, action, **params):
    """Rejoue l'appel avec DryRun=true : l'API valide droits et paramètres sans rien modifier.

    Le SDK retire DryRun de la signature des méthodes générées, d'où le passage par
    gw.raw() qui envoie le payload tel quel. Quand la requête aurait abouti, l'API
    répond par une erreur DryRunOperation : c'est le cas nominal.
    """
    try:
        result = gw.raw(action, DryRun=True, **params)
    except HTTPError as exc:
        if "dryrunoperation" in str(exc).lower():
            log.info("[dry-run] %s validé par l'API (DryRunOperation)", action)
            return True
        log.error("[dry-run] %s refusé par l'API: %s", action, exc)
        return False

    errors = result.get("Errors") if isinstance(result, dict) else None
    if errors:
        if any("dryrun" in str(error.get("Type", "")).lower() for error in errors):
            log.info("[dry-run] %s validé par l'API (DryRunOperation)", action)
            return True
        log.error("[dry-run] %s refusé par l'API: %s", action, errors)
        return False

    log.info("[dry-run] %s validé par l'API: %s", action, result)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["stop", "start"])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_flag("DRY_RUN"),
        help="n'appelle aucune API de modification, journalise seulement ce qui serait fait",
    )
    args = parser.parse_args()

    machine_names = get_worker_machines()
    if not machine_names:
        return
    vm_ids = list(machine_names)
    target_state = TARGET_STATE[args.action]
    log.info("action=%s dry_run=%s vms=%s", args.action, args.dry_run, [describe(v, machine_names) for v in vm_ids])

    gw = Gateway()
    current_states = get_current_states(gw, vm_ids)
    to_process = [vm_id for vm_id in vm_ids if current_states.get(vm_id) != target_state]
    for vm_id in vm_ids:
        if vm_id not in to_process:
            log.info("%s already in state=%s, skipping", describe(vm_id, machine_names), target_state)

    if not to_process:
        log.info("nothing to do, all VMs already in state=%s", target_state)
        return

    if args.dry_run:
        for vm_id in to_process:
            log.info(
                "[dry-run] would %s %s (state=%s)",
                args.action,
                describe(vm_id, machine_names),
                current_states.get(vm_id),
            )
        if not api_dry_run(gw, API_ACTION[args.action], VmIds=to_process):
            sys.exit(1)
        return

    request_power_change(gw, args.action, to_process)

    pending = wait_for_state(gw, to_process, target_state, machine_names)
    if pending:
        log.error(
            "timed out waiting for state=%s on vms=%s",
            target_state,
            sorted(describe(vm_id, machine_names) for vm_id in pending),
        )
        sys.exit(1)

    log.info("all VMs reached state=%s", target_state)


if __name__ == "__main__":
    main()
