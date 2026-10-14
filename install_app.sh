#!/usr/bin/env bash
# Sign and install any .ipa onto Apple TV using a free Apple ID.
#
# Requirements (see README):
#   * config.env with ATV_HOST, ATV_UDID, TEAM_ID, BUNDLE_ID, APPLE_ID
#   * bin/plumesign (signing tool, not in repo)
#   * rp_pairing_file.plist (pairing record, not in repo)
#   * avahi-browse installed
#
# Flow: verify Apple ID login -> discover pairing port via mDNS ->
#       sign + install -> on App ID limit, delete oldest ID and retry.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Load configuration ------------------------------------------------------
if [ -f "$ROOT/config.env" ]; then
  set -a; . "$ROOT/config.env"; set +a
else
  echo "ERROR: $ROOT/config.env missing (template: config.example.env)" >&2
  exit 1
fi

PLUMESIGN="${PLUMESIGN:-$ROOT/bin/plumesign}"
IPA="${IPA:-$ROOT/app-tvos.ipa}"
PAIRING="${PAIRING_FILE:-$ROOT/rp_pairing_file.plist}"
WORKDIR="${WORKDIR:-$ROOT}"
LOG="$WORKDIR/install.log"
TV_NAME="${ATV_NAME:-}"          # mDNS name of Apple TV, e.g., "Living Room"
TV_IP="${ATV_HOST:?ATV_HOST missing in config.env}"
UDID="${ATV_UDID:?ATV_UDID missing in config.env}"
TEAM_ID="${TEAM_ID:?TEAM_ID missing in config.env}"
BUNDLE_ID="${BUNDLE_ID:?BUNDLE_ID missing in config.env}"
APPLE_ID="${APPLE_ID:-}"
PORT="${ATV_PAIRING_PORT:-}"

exec > >(tee -a "$LOG") 2>&1

echo "=============================================="
echo " Install App on Apple TV"
echo " Start: $(date)"
echo "=============================================="

[ -x "$PLUMESIGN" ] || { echo "ERROR: plumesign not found at $PLUMESIGN"; exit 1; }
[ -f "$IPA" ]       || { echo "ERROR: IPA not found at $IPA (see deb_to_ipa.py)"; exit 1; }
[ -f "$PAIRING" ]   || { echo "ERROR: Pairing file not found at $PAIRING"; exit 1; }

# 1) Apple ID login (credentials go directly to Apple, never into the script)
echo "[1/4] Checking Apple ID login..."
if ! "$PLUMESIGN" account list 2>/dev/null | grep -qF "${APPLE_ID%%@*}"; then
  read -r -p "Apple ID Email: " APPLE_EMAIL
  "$PLUMESIGN" account login -u "$APPLE_EMAIL" || { echo "ERROR: Login failed"; exit 1; }
fi
echo "[OK] Login successful"

# 2) Discover pairing port via mDNS
#    The TV only advertises the service when open:
#    Settings -> Remotes and Devices -> Remote App and Devices
echo "[2/4] Discovering pairing port..."
if [ -z "$PORT" ]; then
  for i in $(seq 1 8); do
    for svc in _remotepairing-manual-pairing._tcp _remotepairing._tcp; do
      PORT=$(timeout 8 avahi-browse -rt "$svc" 2>/dev/null \
        | { [ -n "$TV_NAME" ] && grep -A3 "$TV_NAME" || cat; } \
        | grep -oE "port = \[[0-9]+\]" | grep -oE "[0-9]+" | head -1 || true)
      [ -n "$PORT" ] && break
    done
    [ -n "$PORT" ] && break
    echo "     (Attempt $i: Apple TV must be on 'Remote App and Devices' screen)"
    sleep 3
  done
fi
[ -n "$PORT" ] || {
  echo "ERROR: No pairing service found."
  echo "       On Apple TV open: Settings -> Remotes and Devices -> Remote App and Devices"
  exit 1
}
echo "[OK] Port: $PORT"

# 3) Sign + install, with App ID limit fallback
echo "[3/4] Signing and installing (takes a few minutes)..."
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
  echo "     Install failed — attempting App ID limit workaround..."
  OLD_ID=$("$PLUMESIGN" account app-ids 2>/dev/null \
    | grep -B1 "identifier:" | grep -oE '"id: "[A-Z0-9]{10}"' | grep -oE '[A-Z0-9]{10}' | head -1 || true)
  if [ -n "$OLD_ID" ]; then
    echo "     Deleting old App ID: $OLD_ID"
    "$PLUMESIGN" account delete-app-id --app-id-id "$OLD_ID" >/dev/null 2>&1 || true
    sleep 5
    INSTALL && echo "[OK] Installation succeeded after App ID deletion!" \
      || { echo "ERROR: Install still failed after deletion (7-day limit window)"; exit 1; }
  else
    echo "ERROR: No App ID found to delete"
    exit 1
  fi
fi

# 4) Done
rm -f "$ROOT/pin.txt"
echo ""
echo "=============================================="
echo " DONE! The app should now be on your Apple TV."
echo " (Free Apple ID signature valid for 7 days —"
echo "  re-run this script to re-sign)"
echo "=============================================="