# Presse-papiers partagé

Installer **une instance CrossPaste par PC**, pas une par flux Moonlight. Screen1 et Screen2 partagent déjà le presse-papiers de la même session Windows sur l'hôte.

Sur Windows, le kit privilégie maintenant [la version Microsoft Store officielle](https://apps.microsoft.com/detail/9P6X7D7DMCCR). Le Store et la politique locale décident si l'application est autorisée. Un message « stratégie de contrôle d'application » ne se résout pas avec un simple lancement administrateur : terminer l'installation Store ou obtenir l'autorisation de l'administrateur si nécessaire. Si CrossPaste reste bloqué, le lanceur ne prétend pas que le presse-papiers fonctionne et garde la possibilité de lancer les écrans.

Les installateurs du kit activent le démarrage automatique, le chiffrement et la conservation de plusieurs formats. Le client Windows active explicitement texte, HTML, RTF, images et fichiers. L'écoute du presse-papiers est active par défaut ; son état est visible dans CrossPaste.

## Associer une fois

1. Ouvrir CrossPaste sur les deux PC.
2. Dans **Devices**, ajouter le PC distant.
3. Saisir le code affiché sur celui-ci.
4. Vérifier que l'envoi **et** la réception sont permis dans les détails de l'appareil.

Le kit n'associe jamais tous les PC détectés dans un bureau. Chaque collègue associe uniquement son client à sa station. Source : [association et sens de synchronisation CrossPaste](https://crosspaste.com/en/tutorial/devices).

Après association, copier sur un PC puis coller sur l'autre avec les commandes ordinaires. Attendre la fin du transfert pour un fichier volumineux. La destination doit accepter le format enrichi : un éditeur de texte brut ne conserve pas le HTML ou la coloration, même si le presse-papiers les contient.

## Vérifier avant de travailler

Tester dans les deux sens :

1. Un texte avec accents, puis Ctrl+V.
2. Un texte coloré/gras provenant d'une application qui fournit du HTML/RTF, collé dans une application compatible.
3. Une petite image et un petit fichier dans l'Explorateur.

Les limites par défaut de CrossPaste incluent une taille maximale de synchronisation de fichiers de 512 Mo. Les régler dans son interface si nécessaire ; le kit ne désactive pas ces limites. Source : [réglages CrossPaste](https://crosspaste.com/en/tutorial/setting).

## Si les appareils ne se voient pas

CrossPaste utilise normalement TCP 13129 pour ses échanges et la découverte mDNS sur le LAN. Sur Windows, le kit fournit une règle limitée au sous-réseau local ; l'exécuter en administrateur avec le chemin réel :

```powershell
.\windows\Allow-ClipboardNetwork.ps1 -CrossPasteExe "$env:LOCALAPPDATA\ApolloDesktopKit\CrossPaste\bin\CrossPaste.exe"
```

Cela fonctionne aussi si Windows a classé ce LAN comme « Public », sans changer la catégorie de tout le réseau. Pour un VPN, fournir explicitement l'adresse ou le sous-réseau autorisé avec `-RemoteAddress`, voir [réseau](network.md). Le script ne crée aucune redirection sur le routeur.

Dans CrossPaste récent, **Add device manually** accepte une IP et un port. Utiliser cette option sur un VPN sans découverte multicast. Source d'implémentation : [AddDeviceDialog](https://github.com/CrossPaste/crosspaste-desktop/blob/main/app/src/commonMain/kotlin/com/crosspaste/ui/devices/AddDeviceDialog.kt).
