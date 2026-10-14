# atv-sideload

Werkzeuge zum Sideloaden von Apps (getestet mit Kodi) auf einen Apple TV 4K
**ohne Jailbreak**, signiert mit einem kostenlosen Apple-ID-Account.

Läuft komplett lokal auf Linux. Apple-ID-Zugangsdaten gehen ausschließlich an
Apple (`plumesign`), dieses Repo enthält keine Zugangsdaten.

## Wie es funktioniert

1. `.deb`-Build (z. B. Kodi für tvOS) → `.ipa` umpacken (`deb_to_ipa.py`).
2. Pairing-Record des Apple TV (`rp_pairing_file.plist`) bereitstellen.
3. IPA mit `plumesign` signieren und direkt auf den TV installieren
   (`install_kodi.sh`).

Die Signatur eines kostenlosen Apple-Accounts gilt **7 Tage** — danach einfach
`install_kodi.sh` erneut ausführen.

## Voraussetzungen

| Was | Wofür |
|---|---|
| `plumesign` (≥ 2.2.2) unter `bin/plumesign` | Signieren + Installieren. Nicht im Repo — separat beziehen. |
| `avahi-browse` (Paket `avahi-tools`) | Pairing-Port des Apple TV per mDNS finden. |
| Python 3.11 + `pymobiledevice3`, `pycryptodome` | nur für die experimentellen Pairing-Skripte. |
| `ar`, `zip` | `.deb` entpacken bzw. `.ipa` packen. |
| Pairing-Record `rp_pairing_file.plist` | Enthält private Schlüssel → nicht im Repo, selbst erzeugen. |

Der Apple TV veröffentlicht seinen Pairing-Dienst erst, wenn am Gerät
*Einstellungen → Fernbedienungen & Geräte → Remote-App und Geräte* geöffnet
ist. Ohne das findet das Skript keinen Port.

## Konfiguration

```bash
cp config.example.env config.env
$EDITOR config.env        # ATV_HOST, ATV_UDID, TEAM_ID, BUNDLE_ID, APPLE_ID
```

`config.env`, `keys/`, `rp_pairing_file.plist` und alle Binärartefakte sind per
`.gitignore` ausgeschlossen. Prüfen lässt sich die Konfiguration mit:

```bash
python3 atvconfig.py
```

## Benutzung

```bash
# 1) .deb in eine .ipa umpacken
python3 deb_to_ipa.py /pfad/kodi-21.3-tvos.deb -o kodi-tvos.ipa

# 2) signieren und auf den Apple TV installieren
./install_kodi.sh
```

`install_kodi.sh` prüft den Apple-ID-Login, ermittelt den Pairing-Port, ruft
`plumesign sign-rsd` auf und umgeht das App-ID-Limit, indem es bei einem
Fehlschlag die älteste App-ID des Accounts löscht und erneut versucht.
Ausgabe landet zusätzlich in `install.log`.

## Dateien

| Datei | Zweck |
|---|---|
| `atvconfig.py` | zentrale Konfiguration; liest `config.env`, setzt Vendor-Pfade |
| `install_kodi.sh` | signieren + installieren inkl. App-ID-Limit-Fallback |
| `deb_to_ipa.py` | tvOS-`.deb` → `.ipa` |
| `atv_pair.py`, `atv_pair_manual.py` | experimentell: Pairing-Protokoll selbst sprechen |
| `debug_pair.py`, `probe2.py`, `probe_ports.py` | experimentell: Protokoll-/Port-Debugging |
| `scan_*.py` | mDNS-Dienste, Ports und Pairing-IDs des TV auflisten |
| `docs/NOTES.md` | Erkenntnisse, bekannte Fehler, Kommandos |

Die Pairing-Skripte sind Erkundungscode und **nicht** der Weg, der zur
funktionierenden Installation führt — das macht `plumesign`. Details in
`docs/NOTES.md`.

## Lizenz

Privates Projekt, keine Lizenz vergeben.
