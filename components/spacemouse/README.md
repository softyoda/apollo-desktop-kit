# SpaceMouse Link

Application Windows pour utiliser une **3Dconnexion SpaceMouse Compact USB** sur un autre PC, en parallèle de Parsec ou Moonlight. Connexion directe chiffrée en priorité, relais chiffré en secours, sans VPN ni redirection manuelle de ports sur la box.

**Première bêta publique, Windows x64.** Le fonctionnement du prototype avec une vraie Compact a été confirmé ; le nouvel appairage et le cycle de vie desktop sont couverts par les tests décrits dans [SECURITY.md](SECURITY.md). Il ne s'agit pas d'un produit audité indépendamment.

## Installer

Télécharger les installateurs **SpaceMouseLink-Server** et **SpaceMouseLink-Client** dans les [Releases](https://github.com/softyoda/apollo-desktop-kit/releases).

| Rôle | Où l'installer |
|---|---|
| **Server** | Le PC où la SpaceMouse est branchée physiquement |
| **Client** | Le PC qui exécute le logiciel CAD et 3DxWare |

Ces rôles USB sont indépendants des rôles Apollo/Moonlight. Par exemple, le portable Moonlight est généralement le **Server USB**.

1. Fermer les anciennes applications SpaceMouse Link. Le prototype privé utilise un protocole antérieur : il faut mettre à jour les deux postes et refaire l'appairage.
2. Exécuter l'installateur adapté sur chaque PC. L'assistant propose une étape **USB prerequisite** optionnelle, décochée par défaut. La sélectionner pour installer/configurer les pilotes nécessaires. Le téléchargement amont est vérifié par SHA-256 et signature Windows.
3. L'installation initiale du pilote Client peut réinitialiser les hubs USB et demander un redémarrage planifié. Aucun redémarrage automatique n'est effectué.
4. Sur Server, sélectionner la Compact puis **Prepare USB device** : une autorisation administrateur prépare uniquement ce périphérique.
5. Sur Client, installer/configurer le pilote **3DxWare** et les profils de ses logiciels.

L'application réseau s'exécute ensuite **sans droits administrateur**. Les installateurs publics ne contiennent **aucune clé d'appairage**.

## Appairer une seule fois

1. Sur Server, ouvrir **Pairing → Create invitation → Copy invitation**.
2. Copier cette invitation par un canal de confiance et la coller dans **Pairing** sur Client. Elle expire après cinq minutes.
3. Cliquer **Pair with server**. Comparer le même code de vérification sur **les deux écrans** et approuver sur les deux postes. Refuser si les codes diffèrent ou si l'appairage n'a pas été initié par vous.
4. Cliquer **Connect** des deux côtés. Le transport indique **DIRECT** ou **RELAY**. Le RTT est affiché séparément du temps de traitement CAD/vidéo.

Le champ **Device ID** est public : il ne donne pas accès au périphérique. L'invitation, elle, est privée. Après confirmation, chaque profil n'accepte que la clé publique du partenaire enregistré. **Forget trusted peer** révoque cette association et permet un nouvel appairage.

## Zone de notification et préférences

- **Launch at Windows sign-in** : démarrage pour le compte Windows courant, désactivé par défaut.
- **Automatically connect to the last trusted peer** : reconnexion progressive au seul partenaire enregistré, désactivée par défaut.
- **Keep running…** : fermer la fenêtre la masque dans la zone de notification. Le menu de l'icône permet Ouvrir, Connecter, Déconnecter, modifier le démarrage/reconnexion et Quitter.
- **Disconnect** suspend la reconnexion automatique jusqu'à une nouvelle connexion manuelle ou un prochain lancement.
- **Quit** ferme le tunnel et l'application. Le périphérique redevient utilisable localement. Sa préparation USB persistante demeure jusqu'à sa suppression dans usbipd-win.

Les identités et préférences sont chiffrées avec **Windows DPAPI, portée utilisateur**, sous `%LOCALAPPDATA%\SpaceMouseLink\server` ou `client`. Ne pas copier ces dossiers dans le dépôt. Les diagnostics de latence ne contiennent pas de clé ni de données de mouvements.

## Désinstaller

Utiliser **Applications installées** ou le raccourci de désinstallation. L'application, son entrée de démarrage et les données du rôle pour le compte courant sont supprimées. Les pilotes USB et la règle de pare-feu protectrice sont conservés car ils peuvent être utilisés ailleurs ; les désinstaller séparément si nécessaire. Avec plusieurs utilisateurs Windows, chacun doit supprimer ses propres données. Ne pas supprimer la règle protectrice tout en laissant un service USB partagé accessible au réseau.

## Développer

Python 3.13 à jour, environnement virtuel dédié, Inno Setup 7 :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\build.ps1 -Python .\.venv\Scripts\python.exe -Iscc 'C:\Program Files\Inno Setup 7\ISCC.exe'
```

Les builds ne génèrent aucune identité. Les tests unitaires ne nécessitent pas de périphérique. `tests/pairing_smoke.py`, `tests/relay_denied.py` et `tests/relay_smoke.py` utilisent le rendez-vous public avec des clés jetables et des octets synthétiques ; ne pas les lancer dans un réseau interdisant ces services.

Les composants Python conservent leurs licences, collectées lors du build. Les pilotes amont ne sont pas redistribués dans l'installateur : leur installation optionnelle télécharge les versions officielles épinglées. Les binaires personnalisés de cette bêta ne sont pas signés commercialement.
