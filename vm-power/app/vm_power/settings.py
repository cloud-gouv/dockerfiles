"""Lecture des variables d'environnement (alimentées par la ConfigMap de la chart)."""

import os


def env_str(name, default=""):
    return os.environ.get(name, default).strip()


def env_flag(name):
    return env_str(name).lower() in {"1", "true", "yes"}


def env_int(name, default):
    """Entier, ou `default` si la variable est absente ou vide."""
    value = env_str(name)
    return int(value) if value else default


def env_list(name, default):
    """Liste séparée par des virgules. Variable définie mais vide = liste vide."""
    raw = os.environ.get(name)
    raw = default if raw is None else raw
    return [item.strip() for item in raw.split(",") if item.strip()]
