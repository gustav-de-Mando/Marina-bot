# Discord All-in-One Bot

Ein modularer Discord-Bot auf Basis von `discord.py` mit Web-Dashboard, Prefix- und Slash-Commands, SQLite-Persistenz und den in der bereitgestellten Dyno-Liste genannten Command-Funktionen plus zusätzlichen Community-/Utility-Modulen.

## Was enthalten ist

### Dyno-Kommandobasis
Alle 103 Command-Namen aus der bereitgestellten Dyno-Liste sind als **Hybrid-Commands** vorhanden, also über `/command` und den Server-Prefix (standardmäßig `!command`) erreichbar. Darunter:

- Info: `help`, `info`, `ping`, `premium`, `stats`, `uptime`
- Manager: `addemote`, `addmod`, `addrole`, `announce`, `clearwarn`, `command`, `customs`, `delmod`, `delrole`, `giveaway`, Ignore-Regeln, `language`, `module`, `modules`, `prefix`, `purge`, Rollenverwaltung usw.
- Moderation: Ban/Kick/Softban/Unban, Mute/Unmute, Cases, Notes, Warnungen, Lock/Lockdown, Temp-Roles, Role-Persist, Diagnose, Modstats usw.
- Misc: AFK, Avatar, Farben, Invite-Info, Reminder, Highlights, Whois, Serverinfo usw.
- Fun/API: Cat/Dog/Pug, Dad Jokes, GitHub, iTunes, Pokémon, Space/ISS, Poll, RPS usw.
- Rollen: Joinable Ranks, Roleinfo, Rollenlisten
- Levels: Profile, Leaderboard, XP, automatisch erzeugbare Levelrollen
- Tags, Slowmode und Economy

### Zusätzliche All-in-One-Funktionen

- Discord OAuth2 Web-Dashboard
- Pro-Server Prefix
- Modulschalter
- Command Enable/Disable pro Server
- Ignorierte Channels/Rollen/User
- Custom Commands inkl. Dashboard-Verwaltung
- AutoMod: Spam, Caps, Invites, Links, Mass-Mentions, Wortfilter
- Welcome / Goodbye / Autorole
- Persistente Rollen nach Rejoin
- Leveling + XP + Levelrollen
- Tickets
- Suggestions
- Starboard
- Reaction Roles
- Giveaways
- Reminder
- Counting
- Economy mit Wallet/Bank/Daily/Work/Pay/Blackjack
- Musik mit Queue, Skip, Pause, Volume und Loop
- Bump-Reminder
- Konfigurations-Backups
- Umfangreiche Server-Logs

## Dateien

- `bot.py` – Bot-Start, dynamischer Prefix, Slash-Sync und globale Command-Regeln
- `core/storage.py` – SQLite-Schema und Persistenz
- `core/timeparse.py` – Zeitangaben wie `30m`, `2h`, `7d`
- `cogs/` – Funktionsmodule
- `dashboard/app.py` – OAuth2-Dashboard
- `dashboard/templates/` – Dashboard-Oberfläche
- `requirements.txt` – Python-Abhängigkeiten
- `render.yaml` – Render-Deployment
- `.env.example` – benötigte Umgebungsvariablen

## Installation

Python 3.11+ wird empfohlen.

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\\Scripts\\activate

pip install -r requirements.txt
```

Für Musik muss außerdem **FFmpeg** auf dem System installiert und über `PATH` erreichbar sein.

## Discord Developer Portal

Unter **Bot → Privileged Gateway Intents** aktivieren:

- Server Members Intent
- Message Content Intent

Der Bot braucht je nach verwendeten Modulen u. a. folgende Serverrechte:

- Manage Roles
- Manage Channels
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members
- Manage Nicknames
- Manage Emojis and Stickers
- View Audit Log
- Add Reactions
- Connect / Speak

Die Bot-Rolle muss **oberhalb** aller Rollen stehen, die der Bot vergeben, entfernen oder moderieren soll.

## `.env`

`.env.example` kopieren:

```env
DISCORD_TOKEN=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DASHBOARD_SECRET=sehr-langer-zufaelliger-wert
DASHBOARD_URL=http://localhost:8080
PORT=8080
GUILD_ID=
BOT_DB_PATH=data/bot.db
```

`GUILD_ID` ist optional. Wenn gesetzt, werden Slash-Commands zusätzlich in diesen Entwicklungsserver kopiert und dort sofort synchronisiert. Globale Discord-App-Commands können nach Änderungen verzögert sichtbar werden.

## Dashboard / OAuth2

Im Discord Developer Portal unter **OAuth2 → Redirects** eintragen:

```text
https://DEINE-DOMAIN/callback
```

und `DASHBOARD_URL` entsprechend setzen:

```env
DASHBOARD_URL=https://DEINE-DOMAIN
```

Das Dashboard zeigt nur Server, auf denen der Bot vorhanden ist und auf denen der eingeloggte Discord-Nutzer Owner, Administrator oder `Manage Server` besitzt.

Dashboard-Bereiche:

- Module und Prefix
- System-Channels
- AutoMod
- Level-/XP-Einstellungen
- Autorole
- Starboard/Bump
- Welcome/Goodbye
- einzelne Commands an/aus
- Custom Commands

## Levelrollen automatisch erstellen

```text
/levelroles_create
```

oder z. B. bei Prefix `!`:

```text
!levelroles_create
```

Erstellt/verbinden Standardrollen für Level 5, 10, 15, 20, 25, 30, 40, 50, 75 und 100.

Eigene Zuordnung:

```text
/levelrole 25 @Veteran
```

## Custom Commands

Beispiele:

```text
/custom create hallo Hallo {user}! Willkommen auf {server}.
/custom run hallo
/custom delete hallo
```

Mit Prefix kann ein Custom Command zusätzlich direkt aufgerufen werden, z. B. `!hallo`.

Variablen:

- `{user}`
- `{server}`
- `{channel}`

## Persistenz

Standardmäßig wird SQLite unter `data/bot.db` verwendet. Auf Hosting-Plattformen mit **ephemerem Dateisystem** muss `data/` auf einem persistenten Datenträger liegen oder `BOT_DB_PATH` auf einen persistenten Pfad zeigen. Andernfalls können Daten nach Redeploy/Restart verloren gehen.

Die bestehende `data/economy.json` wird für das Economy-Modul weiterverwendet.

## Externe Dienste

Einige Fun-Commands und Musik hängen von Drittanbietern ab (z. B. GitHub API, PokeAPI, iTunes, Tierbild-APIs, yt-dlp/Videoquellen). Ein Ausfall oder eine API-Änderung bei diesen Diensten kann einzelne Commands vorübergehend beeinträchtigen.

## Start

```bash
python bot.py
```

Das Dashboard läuft standardmäßig auf Port `8080`.

## Technische Hinweise

- SQLite ist für einen einzelnen Bot-Prozess geeignet. Bei mehreren Bot-Instanzen/Shards sollte eine zentrale Datenbank wie PostgreSQL verwendet werden.
- Der Code kopiert nicht den proprietären Quellcode von Dyno oder Sapphire. Er implementiert die entsprechenden Funktionen eigenständig.
- Inventur-/Inventory-Commands sind nicht enthalten.
