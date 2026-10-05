# Validation et limites

## Vérifié sur la machine de référence

- Windows, GPU NVIDIA RTX 3090, Apollo 0.4.6, Fleet 0.5.1.
- Création/enregistrement NVAPI du mode 3200 × 1350 à 60 Hz.
- Application du mode, application répétée sans écraser la sauvegarde, restauration, restauration répétée sans effet indésirable.
- Deux sources distinctes, puis montage final écran physique Screen1 + virtuel Screen2.
- CrossPaste 2.2.0 installé, lancé, démarrage automatique et paramètres de synchronisation vérifiés. Une paire de machines reste nécessaire pour valider les transferts réels.
- Le lanceur Windows initial a été utilisé sur un client à deux écrans. Le kit générique ajoute la validation et les profils ; ses nouveaux parcours d'installation demandent une vérification sur chaque machine cible.

## Tests automatisés du dépôt

`tests/Test-Kit.ps1` parse les scripts, compile les interfaces Win32/NVAPI, vérifie la structure des profils et les erreurs de validation, ainsi que les positions calculées avec des résolutions différentes. Les tests Python vérifient le parseur XRandR. Ces tests ne lancent pas de flux et ne modifient pas les écrans.

## Non revendiqué comme testé de bout en bout

- Installation client sur un nouveau PC, association CrossPaste et transfert réel des formats HTML/RTF/fichiers dans les deux sens.
- Installation Apollo/Fleet sur une machine Windows vierge.
- Interface graphique Linux/X11, Wayland et dépendances par distribution.
- WireGuard/WAN sur le réseau d'un collègue.
- Placement hôte appliqué à un autre ensemble de moniteurs.
- Glisser-déposer continu entre sessions : limitation connue, non résolue.

Le guide différencie les fonctions installées, les exemples reproductibles et les extensions à valider. Un test de compilation ne constitue pas une validation du streaming.
