# Client Linux

Un client Linux peut se connecter aux mêmes instances Apollo sur le poste Windows. Cela ne signifie pas que Fleet ou le pilote virtuel SudoVDA sont disponibles pour un **hôte** Linux. Pour héberger sous Linux, partir de la documentation Sunshine et d'une solution d'affichage propre à la distribution ; ce kit ne fournit pas le même montage hôte sous Linux.

## Installer

Prérequis : session de bureau, Python 3, réseau fonctionnel, GPU/décodage pris en charge par Moonlight. Installer `flatpak` avec le gestionnaire de paquets de votre distribution si Moonlight n'est pas déjà disponible.

```bash
bash linux/install-client.sh
```

Le script réutilise `moonlight` s'il existe, sinon installe Moonlight depuis Flathub dans le compte utilisateur. Il télécharge le CrossPaste x86-64 épinglé, vérifie son SHA-256, extrait l'AppImage pour éviter une dépendance à FUSE, puis lance l'application et configure son chiffrement et son démarrage automatique via sa CLI. La première association des appareils reste nécessaire.

Si l'application ne démarre pas, exécuter `~/.local/share/apollo-desktop-kit/crosspaste/squashfs-root/AppRun` depuis le terminal de la session de bureau pour voir l'erreur. Des dépendances graphiques peuvent manquer sur une installation minimale. Le script n'est pas un installateur de serveur sans interface graphique.

## Deux flux avec placement sous X11

Installer `xrandr`, `wmctrl` et `xdotool` avec le gestionnaire de paquets local, puis inspecter :

```bash
xrandr --listmonitors
```

Copier `examples/two-screens.json`, adapter les noms des hôtes et les moniteurs (`left`, `right`, `primary` ou un nom XRandR comme `eDP-1`/`DP-1`) :

```bash
python3 linux/start_desktop.py profile.local.json
```

Moonlight et CrossPaste doivent être associés avant le premier lancement du profil. CrossPaste reste une application indépendante, lancée au démarrage de la session. L'outil X11 attend une fenêtre SDL, la déplace et demande le plein écran au gestionnaire de fenêtres. Cette partie est fournie comme exemple et **n'a pas été testée sur un bureau Linux dans l'environnement de développement de ce dépôt**.

## Wayland

Le script refuse le placement automatique si `XDG_SESSION_TYPE` n'est pas `x11`. `wmctrl` et les commandes X11 ne pilotent pas de manière générale les fenêtres Wayland natives. Utiliser des règles de fenêtres KDE/KWin, Sway, Hyprland ou du compositeur choisi ; la syntaxe et l'identification des fenêtres dépendent de celui-ci.

Il est toujours possible de lancer les sessions avec les arguments Moonlight du profil puis de les placer manuellement. La synchronisation du presse-papiers dépend aussi de la prise en charge de CrossPaste par le bureau utilisé. Sources : [Moonlight Qt](https://github.com/moonlight-stream/moonlight-qt), [CrossPaste](https://crosspaste.com/en/download).
