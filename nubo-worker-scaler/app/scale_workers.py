"""Scale à 0 le soir / restaure le matin les MachineDeployment workers des clusters Cluster API.

Contrairement à l'approche Outscale (extinction des VMs via l'API du cloud), on agit ici
uniquement sur les objets Kubernetes du cluster de management : passer une MachineDeployment
à `replicas: 0` fait supprimer les Machines par CAPI, et donc les instances chez le provider.
Le nombre de replicas d'origine est sauvegardé dans une annotation sur la MachineDeployment
avant la mise à 0, et relu au scale-up : aucune liste de tailles à maintenir à la main.

Les control planes ne sont jamais touchés (seules les MachineDeployment sont patchées),
donc l'API des clusters workload reste joignable la nuit.
"""

import argparse
import logging
import os
import sys
import time

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROUP = "cluster.x-k8s.io"
PLURAL = "machinedeployments"
CLUSTER_NAME_LABEL = "cluster.x-k8s.io/cluster-name"
SAVED_REPLICAS_ANNOTATION = "nubo-worker-scaler.dinum.gouv.fr/previous-replicas"


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}


def env_int(name, default):
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


def env_list(name, default):
    raw = os.environ.get(name)
    raw = default if raw is None else raw
    return [item.strip() for item in raw.split(",") if item.strip()]


INCLUDED_CLUSTER_SUBSTRINGS = env_list("INCLUDED_CLUSTER_SUBSTRINGS", "-wapp-")
EXCLUDED_CLUSTER_SUBSTRINGS = env_list("EXCLUDED_CLUSTER_SUBSTRINGS", "mgmt")
POLL_INTERVAL_SECONDS = env_int("POLL_INTERVAL_SECONDS", 15)
POLL_TIMEOUT_SECONDS = env_int("POLL_TIMEOUT_SECONDS", 900)
# Replicas appliqués au scale-up quand l'annotation manque (0 = ne rien faire).
FALLBACK_REPLICAS = env_int("FALLBACK_REPLICAS", 1)


def build_api():
    """CustomObjectsApi in-cluster.

    Les patchs partent en `application/merge-patch+json` (défaut du client sur les custom
    objects) : les champs absents du corps sont laissés intacts, et une annotation à null
    est supprimée — c'est ce dont on a besoin au scale-up.
    """
    config.load_incluster_config()
    return client.CustomObjectsApi()


def resolve_api_version(api):
    """Version servie pour cluster.x-k8s.io : v1beta1 sur les vieux clusters, v1beta2 depuis CAPI 1.11."""
    forced = os.environ.get("CAPI_API_VERSION", "").strip()
    if forced:
        return forced

    groups = client.ApisApi(api.api_client).get_api_versions().groups
    for group in groups:
        if group.name == GROUP:
            version = group.preferred_version.version
            log.info("version préférée de %s détectée: %s", GROUP, version)
            return version

    log.error("groupe d'API %s absent du cluster : Cluster API n'est pas installé ici", GROUP)
    sys.exit(1)


def cluster_name_of(machine_deployment):
    labels = machine_deployment["metadata"].get("labels", {})
    return labels.get(CLUSTER_NAME_LABEL) or machine_deployment.get("spec", {}).get("clusterName", "")


def in_scope(cluster_name):
    if INCLUDED_CLUSTER_SUBSTRINGS and not any(s in cluster_name for s in INCLUDED_CLUSTER_SUBSTRINGS):
        return False
    return not any(s in cluster_name for s in EXCLUDED_CLUSTER_SUBSTRINGS)


def list_target_machinedeployments(api, version):
    items = api.list_cluster_custom_object(GROUP, version, PLURAL)["items"]
    targets = []
    for md in items:
        cluster_name = cluster_name_of(md)
        if not in_scope(cluster_name):
            log.info("hors périmètre, ignoré: %s (cluster=%s)", describe(md), cluster_name or "inconnu")
            continue
        targets.append(md)

    if not targets:
        log.info(
            "aucune MachineDeployment ne correspond (included=%s excluded=%s), rien à faire",
            INCLUDED_CLUSTER_SUBSTRINGS,
            EXCLUDED_CLUSTER_SUBSTRINGS,
        )
    return targets


def describe(machine_deployment):
    """'default/alpha-sandbox-dev-nubo-01-wapp-01-md-0-az1'."""
    meta = machine_deployment["metadata"]
    return "{}/{}".format(meta["namespace"], meta["name"])


def saved_replicas(machine_deployment):
    annotations = machine_deployment["metadata"].get("annotations") or {}
    raw = annotations.get(SAVED_REPLICAS_ANNOTATION)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        log.warning("annotation %s illisible sur %s: %r", SAVED_REPLICAS_ANNOTATION, describe(machine_deployment), raw)
        return None


def patch(api, version, machine_deployment, body, dry_run):
    meta = machine_deployment["metadata"]
    kwargs = {"dry_run": "All"} if dry_run else {}
    api.patch_namespaced_custom_object(
        GROUP, version, meta["namespace"], PLURAL, meta["name"], body, **kwargs
    )


def get_status(api, version, machine_deployment):
    meta = machine_deployment["metadata"]
    current = api.get_namespaced_custom_object(GROUP, version, meta["namespace"], PLURAL, meta["name"])
    return current.get("status", {})


def wait_for(api, version, expectations):
    """expectations: {md_key: (machine_deployment, predicate, label)}. Retourne ce qui n'a pas convergé."""
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    pending = dict(expectations)
    while pending and time.time() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        for key, (md, predicate, label) in list(pending.items()):
            try:
                status = get_status(api, version, md)
            except ApiException as exc:
                log.warning("lecture du statut de %s impossible: %s", describe(md), exc)
                continue
            if predicate(status):
                log.info("%s a convergé: %s", describe(md), label)
                pending.pop(key)
    return pending


def scale_down(api, version, machine_deployments, dry_run):
    expectations = {}
    failed = []

    for md in machine_deployments:
        name = describe(md)
        replicas = md.get("spec", {}).get("replicas", 0)

        if replicas == 0:
            # Ne surtout pas réécrire l'annotation ici : elle vaudrait 0 et le scale-up
            # du matin remonterait le pool à zéro.
            log.info("%s déjà à 0 replica, ignoré", name)
            continue

        if dry_run:
            log.info("[dry-run] %s passerait de %s à 0 replica", name, replicas)

        body = {
            "metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: str(replicas)}},
            "spec": {"replicas": 0},
        }
        try:
            patch(api, version, md, body, dry_run)
        except ApiException as exc:
            log.error("patch de %s refusé: %s", name, exc)
            failed.append(name)
            continue

        if dry_run:
            log.info("[dry-run] %s validé par l'API (dryRun=All)", name)
            continue

        log.info("%s: %s -> 0 replica (valeur sauvegardée dans %s)", name, replicas, SAVED_REPLICAS_ANNOTATION)
        expectations[name] = (md, lambda status: status.get("replicas", 0) == 0, "0 Machine restante")

    return expectations, failed


def scale_up(api, version, machine_deployments, dry_run):
    expectations = {}
    failed = []

    for md in machine_deployments:
        name = describe(md)
        replicas = md.get("spec", {}).get("replicas", 0)
        previous = saved_replicas(md)

        if replicas != 0:
            if previous is None:
                log.info("%s déjà à %s replicas, ignoré", name, replicas)
            else:
                # Remonté à la main (ou par un helmfile apply) : l'annotation ne sert plus à rien.
                log.info("%s déjà à %s replicas, nettoyage de l'annotation", name, replicas)
                body = {"metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: None}}}
                try:
                    patch(api, version, md, body, dry_run)
                except ApiException as exc:
                    log.warning("nettoyage de l'annotation sur %s impossible: %s", name, exc)
            continue

        target = previous
        if target is None:
            if FALLBACK_REPLICAS <= 0:
                log.warning(
                    "%s est à 0 sans annotation %s et FALLBACK_REPLICAS=0, laissé tel quel",
                    name,
                    SAVED_REPLICAS_ANNOTATION,
                )
                continue
            # Un pool volontairement à 0 et jamais éteint par cet outil remonterait donc
            # à FALLBACK_REPLICAS : mettre FALLBACK_REPLICAS=0 pour l'éviter.
            log.warning("%s est à 0 sans annotation, remontée au fallback %s replicas", name, FALLBACK_REPLICAS)
            target = FALLBACK_REPLICAS

        if dry_run:
            log.info("[dry-run] %s passerait de 0 à %s replicas", name, target)

        body = {
            "metadata": {"annotations": {SAVED_REPLICAS_ANNOTATION: None}},
            "spec": {"replicas": target},
        }
        try:
            patch(api, version, md, body, dry_run)
        except ApiException as exc:
            log.error("patch de %s refusé: %s", name, exc)
            failed.append(name)
            continue

        if dry_run:
            log.info("[dry-run] %s validé par l'API (dryRun=All)", name)
            continue

        log.info("%s: 0 -> %s replicas", name, target)
        expectations[name] = (
            md,
            lambda status, target=target: status.get("readyReplicas", 0) >= target,
            "{} Machine(s) Ready".format(target),
        )

    return expectations, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["down", "up"])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_flag("DRY_RUN"),
        help="rejoue les patchs avec dryRun=All : RBAC et admission sont validés, rien n'est écrit",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        default=env_flag("NO_WAIT"),
        help="ne pas attendre la convergence des Machines, sortir dès les patchs appliqués",
    )
    args = parser.parse_args()

    api = build_api()
    version = resolve_api_version(api)
    machine_deployments = list_target_machinedeployments(api, version)
    if not machine_deployments:
        return

    log.info(
        "action=%s dry_run=%s cibles=%s",
        args.action,
        args.dry_run,
        [describe(md) for md in machine_deployments],
    )

    handler = scale_down if args.action == "down" else scale_up
    expectations, failed = handler(api, version, machine_deployments, args.dry_run)

    if failed:
        log.error("patch impossible sur: %s", sorted(failed))
        sys.exit(1)

    if args.dry_run or args.no_wait or not expectations:
        log.info("action=%s terminée", args.action)
        return

    pending = wait_for(api, version, expectations)
    if pending:
        log.error(
            "toujours pas convergé après %ss: %s",
            POLL_TIMEOUT_SECONDS,
            sorted(pending),
        )
        sys.exit(1)

    log.info("action=%s terminée pour %s MachineDeployment", args.action, len(expectations))


if __name__ == "__main__":
    main()
