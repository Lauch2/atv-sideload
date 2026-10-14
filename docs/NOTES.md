# Project Notes — Apple TV Sideloading

Collected findings from setup. No credentials stored here.

## Background

- Goal: Sideload any tvOS app (e.g., Kodi, Infuse) onto Apple TV 4K without jailbreak, signed with a free Apple ID.
- Free account signature is valid for **7 days** — re-run script to re-sign.
- Use a dedicated secondary Apple ID — keeps the App ID limit off your main account.

## What Works

Signing and installing via `plumesign` (tested with 2.2.2):

```
plumesign sign-rsd --apple-id --register-and-install \
  --udid <UDID> --ip <TV-IP> --port <PAIRING-PORT> \
  --pairing-file rp_pairing_file.plist \
  --package app-tvos.ipa \
  --custom-identifier <BUNDLE-ID>
```

Key points:

- `--port` is the **pairing port**, not 7000. It changes per pairing and must be discovered via mDNS.
- Apple TV only publishes the service when **Settings → Remotes and Devices → Remote App and Devices** is open. Otherwise `avahi-browse` finds nothing.
- Correct mDNS service: `_remotepairing-manual-pairing._tcp` (fallback for already-paired devices: `_remotepairing._tcp`).
- `rp_pairing_file.plist` contains private keys — never commit.

## Known Errors

| Symptom | Meaning / Fix |
|---|---|
| `Error: unexpected response from device: missing port in createListener response` | TV was in inconsistent pairing state — re-open *Remote App and Devices* on TV, re-discover port. |
| No pairing service found (8 attempts) | TV must be on the *Remote App and Devices* screen. |
| Install fails despite valid login | Free tier App ID limit (10 IDs / 7 days). Script deletes oldest App ID and retries. |

## `.deb` → `.ipa`

tvOS builds (Kodi, Infuse, etc.) are distributed as Debian packages. `deb_to_ipa.py` extracts `data.tar.*` directly from the ar archive (no `dpkg` needed), pulls the `.app` from `Applications/` into `Payload/`, and zips to `.ipa`.

## Experimental Scripts

`atv_pair.py`, `atv_pair_manual.py`, `debug_pair.py`, `probe*.py`, and `scan_*.py` document exploration of the pairing protocol (AirPlay port 7000, SRP proof, Remote Pairing from port 50100). They are **not** the path to a working install — that's `plumesign` — and `atv_pair.py` is incomplete (missing TLS/M1/M2 verification). Kept as protocol debugging reference.

## Useful Commands

```bash
# List all pairing-relevant mDNS services of the TV
avahi-browse -rt _remotepairing._tcp
avahi-browse -rt _remoted._tcp          # also yields UDID

# Check TV ports
python3 scan_ports.py

# Show configuration
python3 atvconfig.py
```