# Souris, déplacements et dépannage

## Ne plus déverrouiller la souris à chaque lancement

Le lanceur Windows utilise `--absolute-mouse --display-mode windowed`, puis transforme la fenêtre de droite en plein écran **sans bordures** via Win32. Moonlight continue donc de considérer sa fenêtre comme une fenêtre de bureau, même si elle remplit le moniteur. Il n'est pas nécessaire de simuler `Ctrl+Alt+Shift+L` pour demander ce comportement.

Le code Moonlight initialise le verrouillage en fonction du plein écran exclusif, ou du plein écran avec un seul moniteur. Le mode fenêtre évite cette condition. Voir [`updatePointerRegionLock`](https://github.com/moonlight-stream/moonlight-qt/blob/master/app/streaming/input/mouse.cpp). À vérifier avec la version installée et sans ancienne session déjà passée en plein écran exclusif. Le lancement en fenêtre ne garantit pas que tout gestionnaire de souris tiers conserve le même comportement.

## Pourquoi le drag reste bloqué au bord

Deux fenêtres Moonlight sont deux sessions d'entrée indépendantes. Le code du mode souris absolue borne les coordonnées à la région vidéo de chaque session. Pendant un clic maintenu, la session initiale peut conserver la capture ; l'autre ne reçoit pas nécessairement une séquence cohérente « bouton enfoncé → mouvement → bouton relâché ».

Cela explique qu'il faille parfois relâcher la fenêtre puis la reprendre sur l'autre écran. Modifier la disposition Windows ou enlever le verrouillage du curseur ne suffit pas à résoudre ce cas. Source : [`notifyMouseLeave` et `handleMouseMotionEvent`](https://github.com/moonlight-stream/moonlight-qt/blob/master/app/streaming/input/mouse.cpp).

**Le kit ne prétend pas corriger ce glisser-déposer continu.** Une correction propre nécessiterait un canal d'entrée commun à toutes les vues, capable de conserver l'état des boutons et de convertir les coordonnées vers le bureau hôte entier, ou un client de streaming multiécran intégré. Injecter des clics au changement de fenêtre produirait au contraire des relâchements/pressions artificiels et ne répondrait pas au besoin.

Pour un contributeur souhaitant poursuivre : tester des facteurs de résolution différents, des moniteurs à coordonnées négatives, le DPI mixte, le franchissement avec bouton maintenu, le retour vers une application locale, la déconnexion en cours de drag et la perte de focus. Il faut libérer les boutons à la déconnexion sans créer de clic parasite. Aucune ouverture de service de contrôle réseau supplémentaire n'est faite par ce kit.

## Les raccourcis Windows agissent sur le client

Le lanceur doit inclure `--capture-system-keys always`, et la fenêtre Moonlight doit avoir le focus. Le mode sans bordures est techniquement une fenêtre pour Moonlight : le réglage « capturer uniquement en plein écran » ne suffit donc pas. Fermer puis relancer les flux après mise à jour du script. Avec cette option, Win+flèches et Alt+Tab visent l'hôte quand le flux est actif.

## Deux flux montrent le même écran

Vérifier `Always create Virtual Display` sur Screen2, l'état du pilote SudoVDA et le journal de cette instance. L'option `--resolution` du client ne décide pas de l'écran source. Pour Screen1 physique, vérifier l'identifiant de sortie dans Apollo et désactiver l'option virtuelle de l'application.

## Résolution incorrecte

Comparer le mode demandé et `Desktop resolution`/`Capture size` dans les logs. Le premier décrit la demande du client, les autres la source réellement capturée. Sur l'écran physique, installer le hook de résolution ; sur le virtuel, vérifier le pilote et le facteur Apollo à 100 %.

Si une résolution personnalisée disparaît après un redémarrage/pilote, le hook NVIDIA peut la recréer. Il ne peut pas garantir l'acceptation d'un mode par tous les dongles ou pilotes.

## Apollo Fleet ne s'ouvre pas, mais le streaming marche

Consulter `%ProgramData%\ApolloFleet\logs\startup.log` et `supervisor.log`. Vérifier séparément les processus `sunshine.exe` et les interfaces web. Un crash de la fenêtre Fleet ne signifie pas que les deux instances ont cessé de fonctionner. Un refus d'accès lors du rendu d'une police a notamment été observé sur la machine de référence ; ce kit ne corrige pas ce bug WPF amont.

## Fenêtre au mauvais endroit

Fermer les anciens flux, vérifier les moniteurs Windows et le profil, puis relancer le raccourci. Consulter `desktop-launcher.log`. Si un écran est débranché, le script échoue explicitement plutôt que d'ouvrir toutes les sessions sur le même moniteur. Le flux Linux X11 reste à tester sur le gestionnaire de fenêtres concerné.
