import argparse
import base64
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
CLUSTER_PLURAL = "clusters"
EXCLUDED_CLUSTER_SUBSTRINGS = [
    s.strip() for s in os.environ.get("EXCLUDED_CLUSTER_SUBSTRINGS", "mgmt").split(",") if s.strip()
]


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def get_worker_machines():
    """Retourne {(namespace, cluster): {vm_id: nom de la Machine}}, dans l'ordre renvoyé par l'API Kubernetes."""
    api = client.CustomObjectsApi()
    machine_version = os.environ.get("CAPI_MACHINE_API_VERSION", "v1beta1")
    machines = api.list_cluster_custom_object(MACHINE_GROUP, machine_version, MACHINE_PLURAL)["items"]

    machines_by_cluster = {}
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

        cluster_key = (machine["metadata"]["namespace"], cluster_name)
        machines_by_cluster.setdefault(cluster_key, {})[provider_id.rsplit("/", 1)[-1]] = name

    if not machines_by_cluster:
        log.info("no VM found via '%s/%s %s', nothing to do", MACHINE_GROUP, machine_version, MACHINE_PLURAL)
    return machines_by_cluster


def get_credentials_secret_name(namespace, cluster_name):
    """Nom du Secret de credentials du tenant, tel que CAPOSC l'utilise pour ce cluster.

    Cluster -> spec.infrastructureRef -> OscCluster -> spec.credentials.fromSecret.
    None si l'OscCluster n'en déclare pas : CAPOSC prend alors ses credentials par
    défaut, qui sont ceux du tenant du mgmt (ceux passés au chart).
    """
    api = client.CustomObjectsApi()
    machine_version = os.environ.get("CAPI_MACHINE_API_VERSION", "v1beta1")
    cluster = api.get_namespaced_custom_object(MACHINE_GROUP, machine_version, namespace, CLUSTER_PLURAL, cluster_name)
    infra_ref = cluster["spec"]["infrastructureRef"]
    infra_group, infra_version = infra_ref["apiVersion"].split("/")
    osc_cluster = api.get_namespaced_custom_object(
        infra_group,
        infra_version,
        infra_ref.get("namespace", namespace),
        infra_ref["kind"].lower() + "s",
        infra_ref["name"],
    )
    return osc_cluster.get("spec", {}).get("credentials", {}).get("fromSecret")


def build_gateway(namespace, secret_name):
    """Gateway authentifiée sur le tenant du Secret, ou sur celui du mgmt si secret_name est None."""
    if secret_name is None:
        return Gateway(
            access_key=os.environ["OSC_ACCESS_KEY"],
            secret_key=os.environ["OSC_SECRET_KEY"],
            region=os.environ.get("OSC_REGION", "eu-west-2"),
        )

    data = client.CoreV1Api().read_namespaced_secret(secret_name, namespace).data or {}
    creds = {key: base64.b64decode(value).decode() for key, value in data.items()}
    return Gateway(
        access_key=creds["access_key"],
        secret_key=creds["secret_key"],
        region=creds.get("region") or os.environ.get("OSC_REGION", "eu-west-2"),
    )


def group_by_tenant(machines_by_cluster):
    """Regroupe les VMs par Secret de credentials.

    Retourne {(namespace, secret ou None): (noms des clusters, {vm_id: machine})}. Le nom
    du Secret n'est jamais journalisé : un tenant est désigné par ses clusters.

    Sans PER_TENANT_CREDENTIALS (dev : tous les clusters dans le tenant du mgmt), toutes
    les VMs sont pilotées avec les credentials du chart, sans lire Cluster/OscCluster.

    Retourne aussi la liste des clusters dont les credentials n'ont pas pu être résolus :
    ils sont ignorés sans bloquer les autres.

    Les VMs du tenant du mgmt (secret None) sont placées en dernier : si le mgmt fait
    partie des clusters arrêtés, le Job s'arrête lui-même en les coupant, les autres
    tenants doivent donc être traités avant.
    """
    if not env_flag("PER_TENANT_CREDENTIALS"):
        all_machines = {}
        for machine_names in machines_by_cluster.values():
            all_machines.update(machine_names)
        return {(None, None): (sorted(name for _, name in machines_by_cluster), all_machines)}, []

    tenants = {}
    failed_clusters = []
    for (namespace, cluster_name), machine_names in machines_by_cluster.items():
        try:
            secret_name = get_credentials_secret_name(namespace, cluster_name)
        except Exception:
            log.exception("cluster %s/%s: cannot resolve its credentials, skipping", namespace, cluster_name)
            failed_clusters.append("{}/{}".format(namespace, cluster_name))
            continue
        log.info(
            "cluster %s/%s -> %s credentials",
            namespace,
            cluster_name,
            "tenant" if secret_name else "mgmt (default)",
        )
        tenant_key = (namespace if secret_name else None, secret_name)
        cluster_names, tenant_machines = tenants.setdefault(tenant_key, ([], {}))
        cluster_names.append(cluster_name)
        tenant_machines.update(machine_names)
    return dict(sorted(tenants.items(), key=lambda item: item[0][1] is None)), failed_clusters


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


def power_tenant(gw, action, dry_run, machine_names, tenant):
    """Applique l'action aux VMs d'un tenant. Retourne False en cas d'échec."""
    vm_ids = list(machine_names)
    target_state = TARGET_STATE[action]
    log.info("[%s] action=%s dry_run=%s vms=%s", tenant, action, dry_run, [describe(v, machine_names) for v in vm_ids])

    current_states = get_current_states(gw, vm_ids)
    to_process = [vm_id for vm_id in vm_ids if current_states.get(vm_id) != target_state]
    for vm_id in vm_ids:
        if vm_id not in to_process:
            log.info("[%s] %s already in state=%s, skipping", tenant, describe(vm_id, machine_names), target_state)

    if not to_process:
        log.info("[%s] nothing to do, all VMs already in state=%s", tenant, target_state)
        return True

    if dry_run:
        for vm_id in to_process:
            log.info(
                "[dry-run][%s] would %s %s (state=%s)",
                tenant,
                action,
                describe(vm_id, machine_names),
                current_states.get(vm_id),
            )
        return api_dry_run(gw, API_ACTION[action], VmIds=to_process)

    request_power_change(gw, action, to_process)

    pending = wait_for_state(gw, to_process, target_state, machine_names)
    if pending:
        log.error(
            "[%s] timed out waiting for state=%s on vms=%s",
            tenant,
            target_state,
            sorted(describe(vm_id, machine_names) for vm_id in pending),
        )
        return False

    log.info("[%s] all VMs reached state=%s", tenant, target_state)
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

    config.load_incluster_config()
    machines_by_cluster = get_worker_machines()
    if not machines_by_cluster:
        return

    tenants, failed = group_by_tenant(machines_by_cluster)
    for (namespace, secret_name), (cluster_names, machine_names) in tenants.items():
        tenant = ",".join(cluster_names)
        try:
            gw = build_gateway(namespace, secret_name)
            ok = power_tenant(gw, args.action, args.dry_run, machine_names, tenant)
        except Exception:
            log.exception("[%s] failed", tenant)
            ok = False
        if not ok:
            failed.append(tenant)

    if failed:
        log.error("failed: %s", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
