"""Arrêt le soir / redémarrage le matin des workers des clusters Cluster API.

Le déroulé (lister, planifier, dry-run ou appliquer, attendre la convergence) est commun
et vit dans `providers.base.PowerProvider`. Chaque cloud n'implémente que la façon d'agir
sur ses workers : voir `providers/` et le README pour en ajouter un.
"""
