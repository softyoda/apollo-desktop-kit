# Préparer le poste de travail Windows

L'**hôte** est la station du bureau : GPU, applications et documents. Le **client** est le portable qui reçoit les images. Tous les liens `localhost` ci-dessous s'ouvrent sur l'hôte.

## 1. Installer

Lancer `Install-host.cmd`. Le script vérifie les téléchargements officiels, ouvre l'installation Apollo si absente, puis Fleet si absent, et installe/configure CrossPaste. Valider les demandes UAC et le pilote d'écran virtuel SudoVDA dans l'installation Apollo. Redémarrer si l'installateur le demande.

Un Apollo ou Fleet déjà installé n'est pas remplacé automatiquement. Les versions figées sont indiquées dans `packages.json` ; comparer avec la version existante avant une mise à niveau.

Fleet exige les droits administrateur. Ses réglages, configurations et logs sont dans `%ProgramData%\ApolloFleet`. Activer **Auto Run** pour que Fleet démarre à la connexion Windows. Fleet prend en charge les instances et désactive le service Apollo standard : ce service arrêté n'indique donc pas forcément une panne.

Source : [README de Fleet](https://github.com/drajabr/Apollo-Fleet-Launcher).

## 2. Créer deux instances

Dans Fleet, créer deux instances activées, nommées par exemple `Screen1` et `Screen2`, avec des ports de base **47990** et **48090**. Appliquer. Chaque instance a ses propres fichiers et son propre identifiant ; ne pas copier les certificats ni le fichier d'état d'une autre personne.

Interfaces web pour ces ports :

- Screen1 : `https://localhost:47991/`
- Screen2 : `https://localhost:48091/`

Créer les comptes d'administration dans les interfaces si demandé. Dans Moonlight sur le client, associer **chacune** des deux instances. Si elles ne sont pas découvertes, ajouter `IP_HOTE:47990` et `IP_HOTE:48090`.

## 3. Choisir ce que chaque instance capture

Dans **Applications → Desktop → Modifier** de chaque interface :

| Réglage | Screen1, écran principal/dongle | Screen2, écran virtuel |
|---|---|---|
| Always create Virtual Display | Désactivé | Activé |
| Use App Identity | Désactivé | Activé |
| Facteur de résolution de l'application | 100 % | 100 % |
| Headless mode dans les réglages généraux | Désactivé | Facultatif si l'application impose déjà le virtuel |

Pour Screen1, renseigner **Display Device Id** avec l'identifiant de l'écran physique provenant du journal Apollo. Cet identifiant ressemble à `{...}` ; ce n'est ni le numéro 1 des paramètres Windows ni le nom du GPU. Cela évite que le changement d'écran principal détourne la capture.

Pour deux écrans tous deux virtuels, activer la création d'écran virtuel et l'identité d'application sur les deux `Desktop`. Vérifier que leurs UUID d'application sont différents. Le mode virtuel adopte les dimensions demandées par le client. Source : [écrans virtuels Apollo](https://github.com/ClassicOldSong/Apollo#about-virtual-display).

Enregistrer et redémarrer les instances concernées depuis Fleet ou la page de dépannage Apollo. Modifier un JSON sur disque sans recharger l'instance ne suffit pas.

## 4. Appliquer 3200 × 1350 au dongle à la connexion

À faire seulement sur l'instance physique. Le flux Moonlight `--resolution` ne change pas, à lui seul, le mode d'affichage Windows du dongle.

Sur l'hôte, dans PowerShell **administrateur**, depuis le kit :

```powershell
.\windows\Set-StreamResolution.ps1 -Action Probe -Display '\\.\DISPLAY1'
.\windows\Add-ResolutionHook.ps1 -InstanceName Screen1 -Display '\\.\DISPLAY1' -Width 3200 -Height 1350 -Fps 60 -AllowNvidiaCustomMode
```

Vérifier d'abord que `DISPLAY1` est bien l'écran voulu dans Windows et les logs Apollo. Le script copie son utilitaire dans `%ProgramData%\ApolloDesktopKit`, sauvegarde l'application et ajoute une commande de préparation `Apply` avec une commande de fin `Restore`. Redémarrer ensuite **Screen1** pour charger ce changement.

Au lancement de `Desktop`, le mode est appliqué. À sa fermeture, le précédent est restauré. Activer la fermeture de l'application quand tous les clients se déconnectent (`terminate-on-pause`, option Fleet de suppression à la déconnexion) pour que la restauration corresponde à la fin du travail. Une coupure du processus ou une extinction brutale peut empêcher la commande de fin : relancer manuellement `Set-StreamResolution.ps1 -Action Restore` depuis la copie installée.

`-AllowNvidiaCustomMode` utilise le pilote NVIDIA pour créer et enregistrer le mode **seulement s'il manque**. Sans cette option, le mode doit déjà être proposé par Windows ; cela permet d'utiliser un GPU AMD/Intel avec un mode préexistant. Ne pas attacher deux commandes de résolution concurrentes au même écran.

Dans les réglages Apollo, désactiver le changement automatique de résolution pour ces instances : le hook gère le dongle et SudoVDA gère l'écran virtuel. Ne pas ajouter simultanément un outil tiers qui réécrit les mêmes modes.

Les API utilisées sont documentées par [NVIDIA NVAPI](https://docs.nvidia.com/nvapi/group__dispcontrol.html). Un dongle/pilote différent peut refuser le mode ; l'échec interrompt le lancement et le script tente de restaurer l'état initial.

## 5. Conserver les fenêtres existantes

Une fenêtre ouverte sur l'écran physique reste visible dans Screen1, puisque c'est cet écran qui est capturé. Les fenêtres déplacées vers Screen2 sont sur le même bureau étendu. Si les deux flux montrent le même écran, revoir l'option virtuelle de Screen2 ; si aucun flux ne montre les fenêtres du bureau principal, vérifier que Screen1 n'impose plus un virtuel.
