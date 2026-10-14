# Projektnotizen — Apple-TV-Sideloading

Gesammelte Erkenntnisse aus der Einrichtung. Keine Zugangsdaten hier ablegen.

## Ausgangslage

- Ziel: Kodi (tvOS-Build) ohne Jailbreak auf einen Apple TV 4K 1. Generation
  sideloaden, signiert mit einem kostenlosen Apple-ID-Account.
- Signatur eines kostenlosen Accounts ist **7 Tage** gültig; danach muss neu
  signiert werden (Skript einfach erneut ausführen).
- Apple-ID: bewusst ein ungenutzter Zweitaccount — so bleibt das App-ID-Limit
  des Hauptaccounts unberührt.

## Was funktioniert hat

Signieren und Installieren über `plumesign` (getestet mit 2.2.2):

```
plumesign sign-rsd --apple-id --register-and-install \
  --udid <UDID> --ip <TV-IP> --port <PAIRING-PORT> \
  --pairing-file rp_pairing_file.plist \
  --package kodi-tvos.ipa \
  --custom-identifier <BUNDLE-ID>
```

Wichtig dabei:

- `--port` ist der **Pairing-Port**, nicht 7000. Er wechselt bei jedem
  Pairing-Vorgang und muss per mDNS ermittelt werden.
- Der Apple TV veröffentlicht den Dienst erst, wenn am Gerät
  *Einstellungen → Fernbedienungen & Geräte → Remote-App und Geräte* offen
  ist. Sonst findet `avahi-browse` nichts.
- Passender mDNS-Dienst: `_remotepairing-manual-pairing._tcp`
  (Fallback für bereits gepairte Geräte: `_remotepairing._tcp`).
- `rp_pairing_file.plist` enthält private Schlüssel → niemals committen.

## Bekannte Fehler

| Symptom | Bedeutung / Abhilfe |
|---|---|
| `Error: unexpected response from device: missing port in createListener response` | Im Log vom ersten Durchlauf aufgetreten. Der TV war zu dem Zeitpunkt mit einem anderen Gerät bzw. in einem inkonsistenten Pairing-Zustand — Pairing am TV neu aufbauen und Port neu ermitteln. |
| Kein Pairing-Dienst gefunden (8 Versuche) | Der TV zeigt den Dienst nur im Menü *Remote-App und Geräte*. |
| Installation schlägt fehl, obwohl Login ok | App-ID-Limit des kostenlosen Accounts (10 IDs / 7 Tage). Das Skript löscht dann die älteste App-ID und versucht es erneut. |

## `.deb` → `.ipa`

Die tvOS-Builds von Kodi liegen als Debian-Paket vor. `deb_to_ipa.py`
extrahiert `data.tar.*` direkt aus dem ar-Archiv (kein `dpkg` nötig), packt die
`.app` aus `Applications/` in `Payload/` und zippt das Ganze zur `.ipa`.

## Experimentelle Skripte

`atv_pair.py`, `atv_pair_manual.py`, `debug_pair.py`, `probe*.py` und
`scan_*.py` dokumentieren die Erkundung des Pairing-Protokolls (AirPlay-Port
7000, SRP-Beweis, Remote-Pairing ab Port 50100). Sie sind **nicht** der Weg,
der zur fertigen Installation geführt hat — der läuft über `plumesign` — und
`atv_pair.py` ist unvollständig (TLS-/M1/M2-Verifikation fehlt). Sie bleiben im
Repo als Referenz für Protokoll-Debugging.

## Nützliche Kommandos

```bash
# Alle pairing-relevanten mDNS-Dienste des TV auflisten
avahi-browse -rt _remotepairing._tcp
avahi-browse -rt _remoted._tcp          # liefert auch die UDID

# Ports des TV prüfen
python3 scan_ports.py

# Konfiguration anzeigen
python3 atvconfig.py
```
