# Validation SpaceMouse Link

## Correctif 0.2.0-beta.2

Le contrôle de connexion Server remplace l'énumération privilégiée `Get-NetFirewallRule -PolicyStore ActiveStore` par la lecture COM `HNetCfg.FwPolicy2`. Les profils effectifs restent contrôlés avec `Get-NetFirewallProfile`. Aucun droit administrateur n'est ajouté à l'application et aucune règle n'est modifiée par ce contrôle.

Les 27 tests passent, avec 20 cas de refus du pare-feu : protection absente, désactivée, ambiguë, portée restreinte, politique d'entreprise incompatible ou lecture impossible. La lecture réelle des profils et de la collection COM a été vérifiée dans une session Windows à intégrité moyenne. Sur ce poste Client sans règle Server, la connexion est bien refusée avec un message demandant l'étape USB prerequisite. La réussite avec la règle Server installée sur le PC de la SpaceMouse reste à confirmer sur ce poste.

Référence de l'API : [Microsoft INetFwRule](https://learn.microsoft.com/en-us/windows/win32/api/netfw/nn-netfw-inetfwrule).

Le binaire reconstruit a également passé les diagnostics embarqués de démarrage et de transfert direct synthétique, sans élévation et sans serveur STUN. Ces essais ne remplacent pas le test matériel entre les deux postes.

## Validation précédente : 0.2.0-beta.1

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
