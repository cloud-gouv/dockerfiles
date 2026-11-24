"""Accès aux objets Cluster API du cluster de management, partagé par tous les providers."""

import logging

from kubernetes import client, config

log = logging.getLogger(__name__)

GROUP = "cluster.x-k8s.io"
CLUSTER_NAME_LABEL = "cluster.x-k8s.io/cluster-name"


class CapiError(RuntimeError):
    pass


def describe(obj):
    """'default/alpha-sandbox-dev-nubo-01-wapp-01-md-0-az1'."""
    meta = obj["metadata"]
    return "{}/{}".format(meta["namespace"], meta["name"])


def cluster_name_of(obj):
    labels = obj["metadata"].get("labels") or {}
    return labels.get(CLUSTER_NAME_LABEL) or obj.get("spec", {}).get("clusterName", "")


class CapiClient:
    """CustomObjectsApi in-cluster, restreint aux objets d'un seul cluster workload.

    Les patchs partent en `application/merge-patch+json` (défaut du client sur les custom
    objects) : les champs absents du corps sont laissés intacts, et une annotation à null
    est supprimée.
    """

    def __init__(self, cluster_name, api_version=""):
        if not cluster_name:
            raise CapiError("CLUSTER_NAME vide : refus d'agir sur tous les clusters du mgmt")
        config.load_incluster_config()
        self.api = client.CustomObjectsApi()
        self.cluster_name = cluster_name
        self.version = api_version or self._detect_version()

    def _detect_version(self):
        """v1beta1 sur les vieux clusters, v1beta2 depuis CAPI 1.11."""
        for group in client.ApisApi(self.api.api_client).get_api_versions().groups:
            if group.name == GROUP:
                version = group.preferred_version.version
                log.info("version préférée de %s détectée: %s", GROUP, version)
                return version
        raise CapiError("groupe d'API {} absent du cluster : Cluster API n'est pas installé ici".format(GROUP))

    def list_in_scope(self, plural):
        """Objets `plural` du cluster ciblé, tous namespaces confondus."""
        items = self.api.list_cluster_custom_object(GROUP, self.version, plural)["items"]
        return [obj for obj in items if cluster_name_of(obj) == self.cluster_name]

    def list_namespaced(self, namespace, plural, label_selector):
        return self.api.list_namespaced_custom_object(
            GROUP, self.version, namespace, plural, label_selector=label_selector
        )["items"]

    def get(self, namespace, plural, name):
        return self.api.get_namespaced_custom_object(GROUP, self.version, namespace, plural, name)

    def patch(self, namespace, plural, name, body, dry_run=False):
        kwargs = {"dry_run": "All"} if dry_run else {}
        self.api.patch_namespaced_custom_object(GROUP, self.version, namespace, plural, name, body, **kwargs)
