"""Point d'entrée : python -m vm_power {stop,start} [--provider outscale|nubo] [--dry-run] [--no-wait]"""

import argparse
import logging
import sys

from .capi import CapiClient, CapiError
from .providers import PROVIDERS
from .providers.base import ACTIONS
from .settings import env_flag, env_int, env_str

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("vm_power")


def main():
    parser = argparse.ArgumentParser(prog="vm_power", description=__doc__)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default=env_str("PROVIDER") or None,
        help="cloud des workers (défaut: $PROVIDER)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=env_flag("DRY_RUN"),
        help="fait valider les appels par l'API (DryRun) sans rien modifier",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        default=env_flag("NO_WAIT"),
        help="ne pas attendre la convergence, sortir dès les appels faits",
    )
    args = parser.parse_args()
    if args.provider is None:
        parser.error("provider manquant : --provider ou variable PROVIDER ({})".format(", ".join(sorted(PROVIDERS))))

    try:
        capi = CapiClient(
            cluster_name=env_str("CLUSTER_NAME"),
            api_version=env_str("CAPI_API_VERSION"),
        )
        provider = PROVIDERS[args.provider].from_env(
            capi,
            dry_run=args.dry_run,
            poll_interval_seconds=env_int("POLL_INTERVAL_SECONDS", 15),
            poll_timeout_seconds=env_int("POLL_TIMEOUT_SECONDS", None),
        )
        ok = provider.run(args.action, wait=not args.no_wait)
    except CapiError as exc:
        log.error("%s", exc)
        ok = False

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
