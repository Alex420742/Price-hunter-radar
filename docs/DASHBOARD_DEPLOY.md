# Dashboard & lancement avec Docker

## Dashboard privé
- La page web est servie par le bot sur le port 8080.
- Les endpoints API exigent le header `Authorization: Bearer <DASHBOARD_TOKEN>`.
- L'API est en lecture seule. Les candidats affichés viennent de la Review Queue, pas de deals vérifiés.
- Configure HTTPS via un reverse proxy ou l'hébergeur avant tout accès public. Ne publie jamais le token dans un dépôt ou une URL.

## Lancement local
1. Copie `.env.example` vers `.env`.
2. Renseigne `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` (les secrets Telegram sont nécessaires au processus principal).
3. Crée un token dashboard long et aléatoire, puis définis `DASHBOARD_ENABLED=true` et `DASHBOARD_TOKEN` dans le fichier local `.env`.
4. Lance `docker compose up --build -d`.
5. Ouvre `http://localhost:8080` et saisis le token. Pour un accès extérieur, configure HTTPS et un stockage persistant chez ton hébergeur.

La collecte reste désactivée en dehors des scans manuels; ce guide ne déclenche aucun scan, ne publie rien et ne configure aucune facturation.
