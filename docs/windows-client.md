# Installer et lancer le client Windows

## Installation

Le parcours recommandé est maintenant **un seul fichier `Apollo-Setup.cmd`**, disponible dans les Releases du dépôt. Double-cliquer : le kit s'extrait dans `%LOCALAPPDATA%\ApolloDesktopKit`, installe les applications puis accompagne l'association CrossPaste. Au quotidien, utiliser le raccourci **Apollo - Mes ecrans** ou relancer le même fichier. Un profil personnalisé intégré permet d'éviter toute saisie de résolution ou de nom d'hôte.

Le code CrossPaste reste demandé une seule fois. Le script vérifie qu'un appareil est associé avec envoi et réception autorisés ; il ne présente pas une simple installation comme une synchronisation déjà fonctionnelle. La connexion de bout en bout doit être validée sur les deux PC.

### Parcours ZIP, pour configuration avancée

Extraire le kit dans un dossier permanent, puis lancer `Install-client.cmd`. L'installation utilise `%LOCALAPPDATA%\ApolloDesktopKit`. Une installation Moonlight standard existante est réutilisée, pour conserver ses associations ; sinon le kit télécharge la version portable vérifiée.

CrossPaste est lancé et configuré pour démarrer avec Windows, chiffrer les échanges et conserver les formats enrichis. Il faut associer les deux PC une première fois. Le script ouvre l'assistant d'association en terminal ; le code doit être lu sur l'hôte. Ce code n'est pas intégré au kit.

Le raccourci **Apollo - My screens** est ajouté au bureau. Le profil par défaut se trouve dans `%LOCALAPPDATA%\ApolloDesktopKit\profile.local.json`. Ne pas lancer Moonlight en administrateur : le lanceur du même utilisateur doit pouvoir déplacer ses fenêtres.

## Configurer le profil

Les noms `host` sont ceux visibles dans Moonlight après association ; `app` vaut généralement `Desktop`. Le script ne peut pas deviner ces associations.

```json
{
  "host": "Screen1",
  "app": "Desktop",
  "monitor": "right",
  "mode": "borderless",
  "width": 3200,
  "height": 1350,
  "fps": 60,
  "renderScale": 1.25
}
```

Ce bloc est une entrée du tableau `streams`, pas un profil complet. Voir [`examples/two-screens.json`](../examples/two-screens.json).

`monitor` accepte `left`, `right`, `primary` ou un nom Windows exact tel que `\\.\DISPLAY2`. `left` et `right` désignent les positions dans la disposition Windows, pas l'ordre des numéros affichés par « Identifier ». Si le matériel change, régénérer le profil ou mettre à jour ce champ.

`borderless` remplit l'écran sans bordures ; `windowed` conserve une fenêtre. Tous les flux sont lancés avec le mode souris bureau et une fenêtre SDL, puis le cadre Windows est adapté. Cela évite d'envoyer des raccourcis clavier à une fenêtre qui n'a pas forcément le focus, et évite le verrouillage initial associé au plein écran exclusif.

Les dimensions explicites `width` et `height` font autorité au lancement. `renderScale` documente leur calcul ; modifier ce champ seul ne recalcule pas les dimensions d'un profil existant.

Les commandes activent aussi `--capture-system-keys always` : lorsque la fenêtre Moonlight a le focus, les raccourcis Windows (Win+flèches pour ancrer une fenêtre, Win+Shift+flèches pour changer d'écran, Alt+Tab) sont transmis à l'hôte même en mode fenêtre. Cliquer dans le flux avant de les utiliser. Cela ne corrige pas le glisser-déposer continu entre deux sessions ; c'est la capture du clavier.

## Détecter automatiquement les écrans

Depuis PowerShell, donner un hôte par écran, dans l'ordre gauche → droite puis haut → bas :

```powershell
.\windows\New-ClientProfile.ps1 -Hosts Screen2,Screen1 -RenderScale 1.25 -OutFile .\profile.local.json
.\windows\Install-Client.ps1 -ProfilePath .\profile.local.json
```

Ce générateur utilise la résolution physique détectée et arrondit les dimensions à un nombre pair. Pour un facteur différent par écran, ajuster ensuite les dimensions de chaque entrée. Le profil référence aussi les coordonnées des écrans pour le placement côté hôte.

Pour reproduire le montage de référence, utiliser l'exemple fourni : Screen1 à droite en 3200 × 1350 ; Screen2 à gauche en 1920 × 1008. Le nombre 1008 décrit la résolution du flux de bureau, pas la hauteur exacte de la fenêtre avec sa barre de titre.

## Utilisation quotidienne

1. Connecter les moniteurs ; Windows doit être en bureau **étendu**.
2. Hors bureau, établir le VPN avant le lancement.
3. Double-cliquer sur **Apollo - My screens**.

Fermer les anciennes sessions avant de relancer, pour éviter les doublons. Le lanceur attend les fenêtres de streaming réelles plutôt qu'un délai fixe. En cas d'erreur, il laisse le message visible et écrit `desktop-launcher.log` près du profil.

La session Windows sur l'hôte doit être démarrée, Apollo/Fleet actifs et les deux PC associés. Le lanceur n'allume pas le PC et ne contourne pas l'écran de connexion.
