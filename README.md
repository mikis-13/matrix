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

Taken en SSH-sleutels blijven bewaard in Docker-volumes (`matrix-state` en `matrix-ssh`). De privésleutels zijn niet direct zichtbaar in de bestanden van de host. Bewaar geen wachtzinnen of privégegevens in de repository of in opgestelde configbestanden die door Docker worden gedeeld.

De container draait als niet-root en krijgt geen Docker-socket. Daardoor kan de dashboard-app de Docker-engine van de host niet beheren; Docker-status kan vanuit de container als niet beschikbaar worden gemeld.

SSH-hostchecks en sleutelgeneratie draaien in de container. Voeg geen hosts toe tenzij je de verbinding vanaf deze container verwacht; sleutels staan in het `matrix-ssh`-volume en worden niet automatisch overgezet.

Als je dit vanuit GitHub Codespaces start, draait Docker in de Codespace-omgeving en niet rechtstreeks op je fysieke pc. Om het op je eigen Linux-computer te installeren, clone je de repository daarnet.

<details>
  <summary>Belangrijk: beveiliging voor productie</summary>

  <p>De Compose-configuratie bevat momenteel hardcoded geheime waarden. Dat is niet veilig voor productie:</p>

  <ul>
    <li>de database gebruikt een vaste wachtwoordwaarde zoals <code>matrix</code></li>
    <li>de JWT-sleutel is hardcoded als <code>change-me-super-secret</code></li>
    <li>die waarden staan in de repository en zijn dus voor iedereen zichtbaar</li>
  </ul>

  <p>Als iemand die secret weet, kan die persoon geldige JWT-tokens namaken. Dat is een directe veiligheidsrisico voor authenticatie en autorisatie.</p>

  <p>Gebruik in plaats daarvan echte secrets die niet in versiebeheer worden opgeslagen:</p>

  <pre><code>POSTGRES_PASSWORD=&lt;sterke-unieke-waarde&gt;
JWT_SECRET=&lt;sterke-random-waarde&gt;</code></pre>

  <p>Gebruik een <code>.env</code>-bestand of een secrets manager (bijv. Docker secrets, GitHub Actions secrets, Vault, Doppler of Kubernetes Secrets) en zet dat bestand nooit in Git. Geef ook altijd een voorbeeldbestand mee, bijvoorbeeld <code>.env.example</code>, met placeholder-waarden in plaats van echte geheimen.</p>

  <p>Voorbeeld:</p>

  <pre><code># .env (niet committen)
POSTGRES_DB=matrix
POSTGRES_USER=matrix
POSTGRES_PASSWORD=&lt;veilige-wachtwoord&gt;
JWT_SECRET=&lt;random-waarde&gt;
</code></pre>

  <p>Als deze repo al in gebruik is met echte waarden, vervang de gelekte secrets direct en roteer alle bestaande tokens en wachtwoorden.</p>
</details>
