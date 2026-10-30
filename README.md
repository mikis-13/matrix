# Matrix Control

Matrix Control is a self-hosted operations dashboard for managing infrastructure tasks, authentication flows, background workers, and local services in a homelab or small production environment.

This repository includes:

- a FastAPI-based backend (`api`)
- a background worker (`worker`)
- a PostgreSQL database
- a Redis queue/cache
- a Docker Compose setup for local orchestration

## Overzicht

De applicatie draait in Docker Compose en bestaat uit vier kerncomponenten:

- `api`: HTTP API / backend
- `worker`: achtergrondtaken via Redis Queue
- `postgres`: persistente database
- `redis`: job queue en cache

## Vereisten

Zorg ervoor dat je het volgende hebt:

- Docker Engine
- Docker Compose v2 (`docker compose`)
- Git
- een terminal / shell op je machine

Controleer dit eerst:

```bash
docker --version
docker compose version
```

## Snelle installatie

### 1. Clonen

```bash
git clone https://github.com/mikis-13/matrix.git
cd matrix
```

### 2. Afhankelijkheden starten

```bash
docker compose up -d --build
```

Dit bouwt de containers en start ze in de achtergrond.

### 3. Toegang testen

Na het opstarten kun je de API openen op:

```text
http://localhost:8765
```

De volgende services zijn standaard beschikbaar:

- API: `http://localhost:8765`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Stappen voor een nette lokale setup

### Starten

```bash
docker compose up -d --build
```

### Stoppen

```bash
docker compose down
```

### Logs bekijken

```bash
docker compose logs -f api
```

Voor alle services:

```bash
docker compose logs -f
```

### Services opnieuw opstarten

```bash
docker compose restart
```

## Omgevingsvariabelen

Het project bevat in `compose.yaml` standaardwaarden voor lokale ontwikkeling. Voor productie is het beter om geheime waarden buiten versiebeheer te houden.

Maak een `.env`-bestand in de repository root:

```env
POSTGRES_DB=matrix
POSTGRES_USER=matrix
POSTGRES_PASSWORD=change-me

DATABASE_URL=postgresql://matrix:change-me@postgres:5432/matrix
REDIS_URL=redis://redis:6379/0

JWT_SECRET=change-me-super-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Belangrijk:

- zet `.env` nooit in Git
- gebruik een sterk, uniek wachtwoord voor PostgreSQL
- gebruik een lange willekeurige `JWT_SECRET`

## Volume- en data-opslag

De database-gegevens worden in Docker volumes bewaard, zodat ze niet verloren gaan bij een `docker compose down`.

In de huidige setup zijn er onder andere:

- PostgreSQL data volume
- Redis data volume

Dit is handig voor lokale ontwikkeling en kleine homelab-omgevingen.

## Productie-risico's en beveiliging

Het huidige `compose.yaml` is geschikt voor lokale ontwikkeling, maar niet voor publieke productie zonder extra hardening.

Belangrijkste risico's:

- hardcoded secrets in de compose-configuratie
- database en Redis direct exposen naar host/extern netwerk
- JWT-secret in versiebeheer
- geen HTTPS / reverse proxy
- geen RBAC / MFA / audit logging in de app zelf

### Aanbevolen voor productie

- gebruik een `.env`-bestand of Docker secrets
- zet Postgres en Redis alleen intern in Docker-netwerk
- plaats Traefik of NGINX voor HTTPS
- gebruik RBAC voor admin/operator/viewer rollen
- forceer MFA voor beheeraccounts
- log audit events voor login, token refresh, user actions en SSH access
- backuppen van PostgreSQL en Redis

## Basis productie-architectuur

Voor een veilige homelab/kleine production-opzet is dit het aanbevolen model:

```text
Internet
  │
  ▼
Traefik / NGINX
  │
  ▼
Matrix API
  │
  ├── PostgreSQL (intern)
  ├── Redis (intern)
  └── Worker (intern)
```

Daarbij zijn:

- Traefik of NGINX verantwoordelijk voor HTTPS en reverse proxy
- PostgreSQL en Redis niet publiek bereikbaar
- API en worker alleen via intern Docker-netwerk
- secrets buiten versiebeheer

## Docker-opdrachten

### Starten

```bash
docker compose up -d --build
```

### Stoppen

```bash
docker compose down
```

### Herbouwen na wijzigingen

```bash
docker compose up -d --build
```

### Container status

```bash
docker compose ps
```

### Logs per service

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f postgres
docker compose logs -f redis
```

## Probleemoplossing

### Docker draait niet

Controleer of Docker Engine actief is:

```bash
docker info
```

### Port al in gebruik

Controleer of de poorten 8765, 5432 of 6379 al worden gebruikt:

```bash
lsof -i :8765
lsof -i :5432
lsof -i :6379
```

### Containers herstarten

```bash
docker compose restart
```

### Volumes verwijderen (alle data kwijt)

Gebruik alleen wanneer je echt alles wilt resetten:

```bash
docker compose down -v
```

## Aanbevolen workflow voor ontwikkelomgeving

1. Clone repository
2. Start met `docker compose up -d --build`
3. Controleer `http://localhost:8765`
4. Gebruik logs om fouten te debuggen
5. Pas secrets aan in `.env` voor lokale gebruikers en testing
6. Verplaats naar een beveiligde productie-setup voor publieke toegang

## Samenvatting

De repo is geschikt voor:

- lokale ontwikkeling
- kleine homelab-omgevingen
- test- en staging-omgevingen
- uitbreiding naar een productie-achtige operations platform

Voor echte productie is het belangrijk om:

- secrets te externaliseren
- HTTPS te introduceren
- interne netwerksegregatie toe te passen
- RBAC en MFA te implementeren
- audit logging en backups te activeren

## Volgende stap

Als je wilt, kan ik hierna ook direct een bijgewerkte versie maken van:

- `compose.production.yml`
- `.env.example`
- `traefik.yml`
- een complete `README.md` voor productiegebruik
- een SQL-schema voor users, roles, refresh tokens en audit logs

Die zijn bedoeld om Matrix Control een stuk veiliger en productie-vriendelijker te maken.
