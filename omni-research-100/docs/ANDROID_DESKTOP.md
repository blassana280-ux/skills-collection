# Guide Android / ordinateur

L'interface est une **PWA** servie par le backend lui-même : aucune compilation,
aucun store, aucun serveur frontend séparé.

## Ordinateur

1. Démarrer le backend (`INSTALL.md`).
2. Ouvrir `http://localhost:8000` (ou l'adresse LAN du serveur).
3. Se connecter, choisir FAST / DEEP / MAXIMUM, lancer une recherche.
4. Onglets : *Mission* (agents actifs, vagues, journal), *Sources*,
   *Contradictions*, *Rapport* (markdown + citations + téléchargement .md),
   *Historique*, *Fournisseurs* (activation et test réel), *Paramètres*.

## Android (même réseau Wi-Fi que le serveur)

1. Sur le serveur, démarrer avec `--host 0.0.0.0` (déjà le cas par défaut).
2. Trouver l'IP locale du serveur (`ip addr`, `hostname -I`, par ex.
   `192.168.1.20`).
3. Dans Chrome Android : `http://192.168.1.20:8000`.
4. Menu Chrome → **« Ajouter à l'écran d'accueil » / « Installer l'application »**.
   Le `manifest.webmanifest` fournit le mode `standalone` et l'icône ; le
   service worker ne met en cache **que la coquille statique**, jamais les
   réponses `/api/*` (aucune donnée périmée ou fictive).

> `http://` en LAN suffit pour l'usage local. Pour un accès distant, placer
> l'application derrière un reverse proxy HTTPS (voir `DEPLOYMENT.md`) :
> l'installation PWA et le service worker exigent alors HTTPS.

## Accès distant et reverse proxy

- Les URL de l'interface sont **relatives** (`/api/...`) : aucun appel en dur
  vers `localhost`, donc fonctionnement derrière un proxy ou un hôte
  `https://{port}-{sandbox}.e2b.app`.
- Si le frontend et le backend ont des origines distinctes, renseigner
  `OMNI_CORS_ORIGINS=https://mon-frontend.example`.
- Le flux temps réel utilise `fetch` + `ReadableStream` sur
  `/api/missions/{id}/events` avec l'en-tête `Authorization` (SSE avec
  authentification), avec repli sur un polling réel toutes les 1,5 s.

## Ergonomie mobile

- Champ de saisie en 16 px (pas de zoom automatique iOS/Android),
  `viewport-fit=cover`, cibles tactiles ≥ 42 px, onglets scrollables,
  grille de modes en colonne sous 720 px, tableaux défilants, pied de page
  non fixe sur mobile.

## Dépannage mobile

Voir `TROUBLESHOOTING.md` § « Interface/Android ».
