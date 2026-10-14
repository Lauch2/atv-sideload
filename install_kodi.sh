#!/usr/bin/env bash
# Kodi (oder eine beliebige .ipa) auf den Apple TV signieren und installieren.
#
# Voraussetzungen (siehe README):
#   * config.env mit ATV_HOST, ATV_UDID, TEAM_ID, BUNDLE_ID, APPLE_ID
#   * bin/plumesign (Signier-Tool, nicht im Repo)
#   * rp_pairing_file.plist (Pairing-Record, nicht im Repo)
#   * avahi-browse installiert
#
# Ablauf: Apple-ID-Login prüfen -> Pairing-Port per mDNS finden ->
#         signieren + installieren -> bei App-ID-Limit älteste ID löschen.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Konfiguration laden -----------------------------------------------------
if [ -f "$ROOT/config.env" ]; then
  set -a; . "$ROOT/config.env"; set +a
else
  echo "FEHLER: $ROOT/config.env fehlt (Vorlage: config.example.env)" >&2
  exit 1
fi

PLUMESIGN="${PLUMESIGN:-$ROOT/bin/plumesign}"
IPA="${IPA:-$ROOT/kodi-tvos.ipa}"
PAIRING="${PAIRING_FILE:-$ROOT/rp_pairing_file.plist}"
WORKDIR="${WORKDIR:-$ROOT}"
LOG="$WORKDIR/install.log"
TV_NAME="${ATV_NAME:-}"          # mDNS-Name des Apple TV, z. B. "Wohnzimmer"
TV_IP="${ATV_HOST:?ATV_HOST fehlt in config.env}"
UDID="${ATV_UDID:?ATV_UDID fehlt in config.env}"
TEAM_ID="${TEAM_ID:?TEAM_ID fehlt in config.env}"
BUNDLE_ID="${BUNDLE_ID:?BUNDLE_ID fehlt in config.env}"
APPLE_ID="${APPLE_ID:-}"
PORT="${ATV_PAIRING_PORT:-}"

exec > >(tee -a "$LOG") 2>&1

echo "=============================================="
echo " App auf Apple TV installieren"
echo " Start: $(date)"
echo "=============================================="

[ -x "$PLUMESIGN" ] || { echo "FEHLER: plumesign fehlt unter $PLUMESIGN"; exit 1; }
[ -f "$IPA" ]       || { echo "FEHLER: IPA fehlt unter $IPA (siehe deb_to_ipa.py)"; exit 1; }
[ -f "$PAIRING" ]   || { echo "FEHLER: Pairing-Datei fehlt unter $PAIRING"; exit 1; }

# 1) Apple-ID-Login (Zugangsdaten gehen direkt an Apple, nie ins Skript)
echo "[1/4] Apple-ID-Login prüfen..."
if ! "$PLUMESIGN" account list 2>/dev/null | grep -qF "${APPLE_ID%%@*}"; then
  read -r -p "Apple-ID E-Mail: " APPLE_EMAIL
  "$PLUMESIGN" account login -u "$APPLE_EMAIL" || { echo "FEHLER: Login"; exit 1; }
fi
echo "[OK] Login ok"

# 2) Pairing-Port per mDNS ermitteln
#    Der TV zeigt den Dienst erst, wenn er offen ist:
#    Einstellungen -> Fernbedienungen & Geräte -> Remote-App und Geräte
echo "[2/4] Pairing-Port ermitteln..."
if [ -z "$PORT" ]; then
  for i in $(seq 1 8); do
    for svc in _remotepairing-manual-pairing._tcp _remotepairing._tcp; do
      PORT=$(timeout 8 avahi-browse -rt "$svc" 2>/dev/null \
        | { [ -n "$TV_NAME" ] && grep -A3 "$TV_NAME" || cat; } \
        | grep -oE "port = \[[0-9]+\]" | grep -oE "[0-9]+" | head -1 || true)
      [ -n "$PORT" ] && break
    done
    [ -n "$PORT" ] && break
    echo "     (Versuch $i: Apple TV muss im Menü 'Remote-App und Geräte' sein)"
    sleep 3
  done
fi
[ -n "$PORT" ] || {
  echo "FEHLER: Kein Pairing-Dienst gefunden."
  echo "       Am Apple TV öffnen: Einstellungen -> Fernbedienungen & Geräte -> Remote-App und Geräte"
  exit 1
}
echo "[OK] Port: $PORT"

# 3) Signieren + installieren, mit App-ID-Limit-Fallback
echo "[3/4] Signieren und installieren (dauert einige Minuten)..."
export PLUMESIGN_TEAM_ID="$TEAM_ID"

INSTALL() {
  "$PLUMESIGN" sign-rsd \
    --apple-id --register-and-install \
    --udid "$UDID" --ip "$TV_IP" --port "$PORT" \
    --pairing-file "$PAIRING" \
    --package "$IPA" \
    --custom-identifier "$BUNDLE_ID" \
    --output-provision "$WORKDIR/embedded.mobileprovision"
}

if ! INSTALL; then
  echo "     Installationsfehler — versuche App-ID-Limit zu umgehen..."
  OLD_ID=$("$PLUMESIGN" account app-ids 2>/dev/null \
    | grep -B1 "identifier:" | grep -oE '"id: "[A-Z0-9]{10}"' | grep -oE '[A-Z0-9]{10}' | head -1 || true)
  if [ -n "$OLD_ID" ]; then
    echo "     Lösche alte App-ID: $OLD_ID"
    "$PLUMESIGN" account delete-app-id --app-id-id "$OLD_ID" >/dev/null 2>&1 || true
    sleep 5
    INSTALL && echo "[OK] Installation nach App-ID-Löschung erfolgreich!" \
      || { echo "FEHLER: Installation auch nach Löschung fehlgeschlagen (Limit-Fenster 7 Tage)"; exit 1; }
  else
    echo "FEHLER: Keine App-ID zum Löschen gefunden"
    exit 1
  fi
fi

# 4) Fertig
rm -f "$ROOT/pin.txt"
echo ""
echo "=============================================="
echo " FERTIG! Die App sollte jetzt auf dem Apple TV sein."
echo " (Signatur eines kostenlosen Apple-ID-Accounts: 7 Tage gültig —"
echo "  Skript erneut ausführen zum Neusignieren)"
echo "=============================================="
