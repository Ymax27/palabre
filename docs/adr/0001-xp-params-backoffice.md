# ADR 0001 — Paramètres XP en constantes jusqu'au back-office

## Statut

Accepté (2026-11-05).

## Contexte

PLAN.md §2 J prévoit un back-office « paramètres XP » dans la fenêtre du **06 au 09/11**. Le barème et les plafonds vivent aujourd'hui dans `app/services/xp.py`.

## Décision

Garder les constantes (`AWARDS`, `DAILY_CAP`, anti-réciprocité, seuils de réputation) dans `xp.py` jusqu'à ce back-office. Pas de table `xp_params` ni d'UI admin dans cette tranche.

## Conséquences

- Calibration rapide possible par PR sur `xp.py`.
- Migration vers une table admin prévue 06–09/11 sans changer l'API de `grant_xp`.
