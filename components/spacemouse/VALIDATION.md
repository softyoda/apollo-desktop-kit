# Validation de la bêta 0.2.0-beta.1

Vérifications effectuées le 12 octobre 2026 sur Windows x64.

| Contrôle | Résultat |
|---|---|
| Runtime du binaire public | CPython 3.13.16 |
| Tests unitaires protocole, cryptographie, identité, DPAPI, démarrage et CLI | 25 réussis |
| Appairage synthétique avec confirmations des deux côtés | Clés correctement enregistrées et même secret dérivé |
| Refus de confirmation d'un côté | Aucune association enregistrée |
| Attaquant ayant le secret de connexion mais pas la clé privée approuvée | Refus avant ouverture USB ou transport |
| Binaire packagé : démarrage et transfert direct synthétique | Réussis, sans élévation |
| Icône Windows réelle, fermeture vers notification, restauration, Quitter | Réussis |
| Client USB natif sans élévation | Requête reçue par un serveur local de test qui refuse l'import ; aucun périphérique réel attaché |
| Audit pip-audit des 49 dépendances verrouillées | Aucune vulnérabilité connue signalée à cette date |
| Compilation des assistants Server/Client avec désinstalleur | Réussie |
| Tests existants Apollo/Moonlight/CrossPaste et lanceur Linux | Réussis après séparation des composants |

Les essais de transport utilisent deux instances sur un même PC et des octets synthétiques. Ils ne constituent pas une mesure WAN entre deux sites. Le prototype précédent a été validé avec une vraie SpaceMouse par l'utilisateur ; la nouvelle distribution et son appairage doivent encore être essayés ensemble sur les deux postes de destination.

L'audit des dépendances Python ne couvre pas tous les composants natifs de Windows, les pilotes USB ou l'ensemble des bibliothèques FFmpeg embarquées par PyAV. Aucun audit indépendant, test d'intrusion tiers ou preuve formelle n'est revendiqué. Le détail du modèle de confiance est dans [SECURITY.md](SECURITY.md).

Les installateurs sont génériques : aucune invitation, identité privée ou association du prototype n'est incluse. L'installation et la préparation USB restent des actions explicites de l'utilisateur ; les pilotes de la session de travail n'ont pas été réinstallés pendant cette validation.
