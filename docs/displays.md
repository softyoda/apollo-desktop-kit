# Résolution, échelle et disposition

## Trois réglages distincts

| Réglage | Ce qu'il change |
|---|---|
| Résolution du bureau hôte | Nombre de pixels des applications capturées |
| Résolution demandée à Moonlight | Dimensions du flux vidéo ; ne crée pas un mode sur un écran physique |
| Échelle Windows, par exemple 125 % | Taille logique des textes et contrôles sur le bureau hôte |

L'exemple utilise un **flux à 1,25 fois les dimensions du moniteur client**. Sur un écran 2560 × 1080, cela donne 3200 × 1350 ; le GPU hôte calcule plus de pixels et Moonlight réduit l'image. À échelle Windows inchangée, cela augmente l'espace disponible et réduit la taille apparente des éléments. C'est le réglage retenu ici pour travailler ; il ne garantit pas de rendre le texte plus gros.

Pour des textes plus grands, ajuster séparément l'échelle Windows sur l'écran distant concerné. L'option de résolution `scale-factor` d'Apollo est encore un autre multiplicateur : la laisser à 100 % dans ce montage pour ne pas appliquer deux fois le facteur 1,25.

## Même ordre sur les deux machines

Ouvrir les deux flux avant de régler les écrans hôtes : le virtuel de Screen2 n'existe pas nécessairement avant sa connexion. Dans **Paramètres Windows → Système → Affichage**, cliquer sur **Identifier**, placer Screen2 à gauche et Screen1 à droite, puis aligner leurs bords supérieurs. Garder l'écran physique comme principal si l'on veut conserver ses fenêtres.

Avec l'identité d'application virtuelle stable, Windows peut mémoriser cette disposition pour les prochaines connexions. « Principal » n'a pas besoin d'être le même écran sur le client et l'hôte : dans l'exemple le portable gauche est principal localement, mais l'écran physique droit reste principal sur l'hôte.

## Aide au placement reproductible

Copier le profil client sur l'hôte. Identifier les noms Windows actuels des écrans dans les logs Apollo, puis exécuter **sur l'hôte** :

```powershell
.\windows\Align-HostScreens.ps1 -ProfilePath .\profile.local.json -DisplayMap @{ Screen1='\\.\DISPLAY1'; Screen2='\\.\DISPLAY6' } -AnchorHost Screen1
```

Cette commande affiche un aperçu, sans modifier l'affichage. Remplacer `DISPLAY6` par l'écran virtuel réellement créé ; ne pas copier ce numéro aveuglément. Ajouter `-Apply` pour enregistrer les positions. Les anciennes positions sont sauvegardées et un échec tente une restauration.

L'outil aligne une **rangée horizontale** ou une **colonne verticale** (`-Layout Vertical`), dans l'ordre du profil client, sans trou entre les écrans. Les dimensions de chaque flux sont prises en compte : avec 1920 × 1008 à gauche et 3200 × 1350 à droite, l'hôte peut utiliser x=-1920 pour le premier et x=0 pour le second. Il ne multiplie pas toutes les coordonnées par un facteur unique, ce qui provoquerait des chevauchements avec des échelles différentes.

Les dispositions en L, les décalages verticaux libres et les rotations explicites se règlent pour l'instant dans Windows. L'outil ne prétend pas reproduire automatiquement une topologie arbitraire. Les profils portrait conservent leurs dimensions hauteur/largeur ; l'orientation physique se règle dans le système du client avant la génération.

La disposition géométrique ne suffit pas à corriger le glisser-déposer entre deux sessions Moonlight : voir [les limites d'entrée](troubleshooting.md).
