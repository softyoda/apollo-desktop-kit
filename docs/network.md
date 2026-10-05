# Depuis le bureau, la maison ou un autre réseau

Le streaming n'est pas limité au LAN. Pour reproduire ce montage hors bureau, privilégier **un VPN d'entreprise ou WireGuard** : une fois le tunnel établi, Moonlight et CrossPaste joignent les adresses privées du poste. Le kit ne modifie ni le routeur ni le VPN de l'entreprise.

## Parcours recommandé : VPN

1. Faire installer/configurer le VPN autorisé par votre bureau sur le poste et le client, ou utiliser une passerelle VPN donnant accès au LAN de la station.
2. Attribuer des adresses stables. Exemple fictif : hôte `10.77.0.1`, client `10.77.0.2`.
3. Connecter le VPN avant le raccourci de streaming.
4. Dans Moonlight, ajouter manuellement `10.77.0.1:47990` et `10.77.0.1:48090`. Associer chaque instance. La découverte multicast ne traverse généralement pas un tunnel routé.
5. Dans CrossPaste, utiliser **Add device manually**, IP `10.77.0.1`, port `13129`, et effectuer l'association. Choisir l'interface VPN dans ses paramètres réseau si la mauvaise adresse est annoncée.
6. Autoriser le trafic sur l'hôte depuis le pair/sous-réseau VPN, et non uniquement `LocalSubnet` si le VPN est routé.

Sur Windows, exemple pour CrossPaste dans PowerShell administrateur :

```powershell
.\windows\Allow-ClipboardNetwork.ps1 -CrossPasteExe "$env:LOCALAPPDATA\ApolloDesktopKit\CrossPaste\bin\CrossPaste.exe" -RemoteAddress LocalSubnet,10.77.0.2
```

Le même réglage est nécessaire dans l'autre sens si le pare-feu du client bloque les connexions de l'hôte. La découverte mDNS n'est pas indispensable quand on ajoute les appareils par IP.

## Exemple WireGuard point à point

Ce modèle est destiné à l'administrateur réseau. Remplacer les clés et adresses ; **ne jamais publier les clés privées**. Un endpoint doit être joignable depuis l'autre PC (adresse publique/redirection UDP ou passerelle appropriée).

Hôte/passerelle directement joignable, exemple minimal :

```ini
[Interface]
PrivateKey = CLE_PRIVEE_HOTE
Address = 10.77.0.1/24
ListenPort = 51820

[Peer]
PublicKey = CLE_PUBLIQUE_CLIENT
AllowedIPs = 10.77.0.2/32
```

Client :

```ini
[Interface]
PrivateKey = CLE_PRIVEE_CLIENT
Address = 10.77.0.2/24

[Peer]
PublicKey = CLE_PUBLIQUE_HOTE
Endpoint = vpn.example.org:51820
AllowedIPs = 10.77.0.1/32
PersistentKeepalive = 25
```

`AllowedIPs` doit correspondre au routage réel. Si le serveur VPN est une passerelle distincte de la station, il faut aussi le routage vers le LAN et le chemin retour ; cet exemple ne les configure pas. Deux réseaux LAN utilisant le même sous-réseau peuvent créer un conflit de routes. `PersistentKeepalive = 25` est utile pour le pair derrière NAT, pas une obligation universelle. Sources : [WireGuard Quick Start](https://www.wireguard.com/quickstart/), [wg-quick](https://git.zx2c4.com/wireguard-tools/about/src/man/wg-quick.8).

Un accès sous CGNAT ne devient pas joignable par une simple redirection de port. Utiliser la passerelle VPN de l'entreprise, un endpoint joignable, ou un service de VPN maillé approprié. Le choix et les accès relèvent de l'administrateur du réseau.

## Ports des deux instances Apollo de référence

Ces ports sont calculés pour **Apollo 0.4.6**, avec des bases **47990 et 48090**. Le port par défaut de Sunshine classique est différent : ne pas recopier ses nombres sans tenir compte du décalage.

| Fonction | Protocole | Base 47990 | Base 48090 |
|---|---|---|---|
| API HTTPS du protocole de streaming | TCP | 47985 | 48085 |
| API HTTP du protocole de streaming | TCP | 47990 | 48090 |
| Négociation RTSP | TCP | 48011 | 48111 |
| Vidéo | UDP | 47999 | 48099 |
| Contrôle | UDP | 48000 | 48100 |
| Audio | UDP | 48001 | 48101 |
| Interface web d'administration | TCP | 47991 | 48091 |

Sources du calcul : [nvhttp.h](https://github.com/ClassicOldSong/Apollo/blob/0cd32abaaa141d262477d039ac447b38fe99c394/src/nvhttp.h), [stream.h](https://github.com/ClassicOldSong/Apollo/blob/0cd32abaaa141d262477d039ac447b38fe99c394/src/stream.h), [rtsp.h](https://github.com/ClassicOldSong/Apollo/blob/0cd32abaaa141d262477d039ac447b38fe99c394/src/rtsp.h). D'autres versions ou fonctions peuvent utiliser des ports supplémentaires ; vérifier les journaux et les ports réellement écoutés.

Sur le VPN, autoriser les ports de streaming depuis les pairs concernés. L'interface web d'administration sert à configurer/associer : la conserver sur l'hôte ou sur un réseau d'administration autorisé. CrossPaste utilise TCP 13129 par défaut ; ce port est indépendant de chaque instance Apollo.

## WAN direct, sans VPN

C'est techniquement possible pour Moonlight avec une adresse publique joignable et des redirections des ports de streaming **de chaque instance**, à faire valider par l'administrateur. Le VPN reste le parcours documenté pour l'ensemble streaming + presse-papiers. Ne pas exposer l'interface web Apollo ni CrossPaste directement sur Internet pour reproduire cet exemple. Ce dépôt ne crée pas automatiquement de redirection et n'active pas UPnP.

La documentation [Moonlight — streaming sur Internet](https://github.com/moonlight-stream/moonlight-docs/wiki/Setup-Guide#streaming-over-the-internet) décrit aussi des méthodes adaptées à Sunshine/GameStream. Adapter à la version Apollo et aux ports Fleet au lieu d'installer plusieurs mécanismes de redirection concurrents.

## Qualité et dépannage hors bureau

Les débits des deux flux **s'additionnent**, ainsi que les transferts CrossPaste. La liaison montante du bureau et la latence du trajet comptent autant que le débit descendant à domicile. Commencer à 60 FPS avec un débit raisonnable, puis augmenter selon les statistiques ; les scripts conservent le codec et le débit par défaut de Moonlight, ils ne garantissent pas un débit WAN adapté.

Un `Test-NetConnection 10.77.0.1 -Port 47990` réussi vérifie un port TCP, pas la vidéo UDP. Si l'association fonctionne mais pas l'image, vérifier les règles UDP, le routage et la taille MTU du VPN. Tester d'abord un seul flux. Ne pas désactiver tous les pare-feu pour diagnostiquer.
