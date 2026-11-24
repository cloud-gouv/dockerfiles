# vm-power

Arrête le soir et redémarre le matin les workers d'un cluster Cluster API, depuis son
cluster de management. Image unique, un provider par cloud. Déployée par la chart
`common-helm-charts/vm-power`, une release par cluster workload.

| provider   | ce que fait `stop`                                   | ce que fait `start`                                  |
|------------|------------------------------------------------------|------------------------------------------------------|
| `outscale` | `StopVms` sur les VMs des Machines CAPI              | `StartVms`                                           |
| `nubo`     | MachineDeployment à `replicas: 0` (taille sauvée en annotation) | restaure la taille depuis l'annotation   |

Sur nubo, une VM arrêtée reste facturée : il faut la supprimer, d'où le scale à 0.

## Utilisation

```sh
python -m vm_power stop --provider nubo --dry-run
```

| Variable                      | Défaut           | Rôle                                                        |
|-------------------------------|------------------|-------------------------------------------------------------|
| `PROVIDER`                    | —                | `outscale` ou `nubo` (ou `--provider`)                      |
| `DRY_RUN`                     | `false`          | fait valider les appels par l'API sans rien modifier        |
| `NO_WAIT`                     | `false`          | sort sans attendre la convergence                           |
| `CLUSTER_NAME`                | — (obligatoire)  | cluster workload ciblé (label `cluster.x-k8s.io/cluster-name`) |
| `CAPI_API_VERSION`            | détectée         | forcer `v1beta1` / `v1beta2`                                |
| `POLL_INTERVAL_SECONDS`       | `15`             |                                                             |
| `POLL_TIMEOUT_SECONDS`        | selon provider   | 300 (outscale), 900 (nubo)                                  |
| `OSC_ACCESS_KEY` `OSC_SECRET_KEY` `OSC_REGION` | — | outscale uniquement                                    |
| `FALLBACK_REPLICAS`           | `1`              | nubo : taille au start si l'annotation manque (0 = rien)    |
| `SKIP_NODE_DRAIN`             | `false`          | nubo : supprime les Machines sans drain ni attente des volumes |

## Structure

```
app/vm_power/
├── __main__.py          CLI, construit le CapiClient et le provider
├── capi.py              accès aux objets cluster.x-k8s.io, filtrage des clusters exclus
├── settings.py          lecture des variables d'environnement
└── providers/
    ├── __init__.py      registre PROVIDERS
    ├── base.py          PowerProvider (classe abstraite) + déroulé commun run()
    ├── outscale.py
    └── nubo.py
```

`PowerProvider.run()` enchaîne : `list_targets()` → `plan()` → `validate()` (dry-run)
ou `apply()` puis `converged()` en boucle jusqu'au timeout.

## Ajouter un provider

1. Créer `providers/<cloud>.py` avec une classe qui hérite de `PowerProvider`,
   définit `name = "<cloud>"` et implémente les cinq méthodes abstraites :
   `list_targets`, `plan`, `validate`, `apply`, `converged`.
2. Surcharger `from_env()` si le provider a ses propres variables d'environnement.
3. L'ajouter dans `PROVIDERS` (`providers/__init__.py`) et ses dépendances dans
   `requirements.txt`.
4. Côté chart : ajouter la valeur dans l'`enum` de `values.schema.json`, et les règles
   RBAC / variables d'environnement nécessaires.
