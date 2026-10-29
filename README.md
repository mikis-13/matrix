# Matrix Control

## Lokaal starten met Docker

Vereist Docker Engine en Docker Compose. Start vanuit de repositorymap:

```sh
docker compose up -d --build
```

Open daarna http://localhost:8765. De Compose-configuratie gebruikt Linux host networking, terwijl de app zelf aan `127.0.0.1` bindt. Stoppen kan met:

```sh
docker compose down
```

Taken en SSH-sleutels blijven bewaard in Docker-volumes (`matrix-state` en `matrix-ssh`). De privésleutels zijn niet direct zichtbaar in de bestanden van de host. Bewaar geen wachtzinnen of privésleutels in deze publieke repository.

De container draait als niet-root en krijgt geen Docker-socket. Daardoor kan de dashboard-app de Docker-engine van de host niet beheren; Docker-status kan vanuit de container als niet beschikbaar worden getoond. Dit is bewust: toegang tot de Docker-socket geeft in de praktijk vrijwel volledige beheerdersrechten op de host. De app voert verder geen vrije shellcommando's uit.

SSH-hostchecks en sleutelgeneratie draaien in de container. Voeg geen hosts toe tenzij je de verbinding vanaf deze container verwacht; sleutels staan in het `matrix-ssh`-volume en worden niet automatisch naar een server gekopieerd.

Als je dit vanuit GitHub Codespaces start, draait Docker in de Codespace-omgeving en niet rechtstreeks op je fysieke pc. Om het op je eigen Linux-computer te installeren, clone je de repository daar en voer je bovenstaande Docker Compose-opdracht lokaal uit.



