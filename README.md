# atv-sideload

Sideload iOS/tvOS apps (tested with Kodi) onto **Apple TV 4K** without jailbreak, using a free Apple ID for code signing.

Runs entirely on Linux. Your Apple ID credentials are only ever sent to Apple via `plumesign` — this repository contains no secrets.

---

## How It Works

1. **Convert** a tvOS `.deb` (e.g., Kodi build) → `.ipa` using `deb_to_ipa.py`
2. **Prepare** the Apple TV pairing record (`rp_pairing_file.plist`)
3. **Sign & install** the IPA directly onto the Apple TV using `plumesign` via `install_kodi.sh`

A free Apple Developer account signature is valid for **7 days** — just re-run `install_kodi.sh` to renew.

---

## Features

- ✅ **No jailbreak required** — uses standard Apple TV pairing & signing
- ✅ **Automatic pairing port discovery** via mDNS (`avahi-browse`)
- ✅ **App ID limit workaround** — auto-deletes oldest App ID when limit (10/7 days) is hit
- ✅ **Config-driven** — all device/secrets in gitignored `config.env`
- ✅ **Deb-to-IPA conversion** without `dpkg` (pure Python `ar` + `tar` parsing)

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| `plumesign` ≥ 2.2.2 | Signing + installation (not in repo) | Download separately → `bin/plumesign` |
| `avahi-browse` | Discover Apple TV pairing port via mDNS | `apt install avahi-tools` / `dnf install avahi-tools` |
| `ar`, `zip` | Extract `.deb`, create `.ipa` | `binutils`, `zip` |
| Python 3.11 + `pymobiledevice3`, `pycryptodome` | Experimental pairing/debug scripts only | `pip install -r requirements.txt` |

> **Important:** The Apple TV only advertises its pairing service when **Settings → Remotes and Devices → Remote App and Devices** is open on the TV. Without this, no pairing port will be found.

---

## Quick Start

```bash
# 1) Clone & configure
git clone https://github.com/Lauch2/atv-sideload.git
cd atv-sideload
cp config.example.env config.env
$EDITOR config.env   # Set ATV_HOST, ATV_UDID, TEAM_ID, BUNDLE_ID, APPLE_ID

# 2) Verify config
python3 atvconfig.py

# 3) Convert tvOS .deb → .ipa
python3 deb_to_ipa.py /path/to/kodi-21.3-tvos.deb -o kodi-tvos.ipa

# 4) Sign & install on Apple TV
./install_kodi.sh
```

Output is also logged to `install.log`.

---

## Configuration

All machine-specific values live in `config.env` (gitignored):

```bash
# Apple TV
ATV_HOST=appletv.local          # or IP (e.g., 192.168.x.x)
ATV_NAME=Wohnzimmer             # mDNS name for service discovery
ATV_UDID=YOUR_UDID_HERE
ATV_PAIRING_PORT=               # empty = auto-discover

# Apple Developer (free tier)
TEAM_ID=YOUR_TEAM_ID
BUNDLE_ID=com.example.yourbundle
APPLE_ID=your-unused-apple-id@example.com
```

Run `python3 atvconfig.py` to verify all values load correctly.

---

## Scripts Overview

| File | Purpose |
|------|---------|
| `atvconfig.py` | Central config loader; reads `config.env`, sets vendor `sys.path` |
| `install_kodi.sh` | Main entrypoint: login check → port discovery → `plumesign sign-rsd` → install + App ID fallback |
| `deb_to_ipa.py` | Extract `.app` from tvOS `.deb` → package as `.ipa` (no `dpkg` needed) |
| `scan_*.py` | mDNS service discovery, port scanning, pairing ID lookup |
| `atv_pair.py`, `atv_pair_manual.py` | **Experimental** — raw pairing protocol (SRP, TLS) — incomplete |
| `debug_pair.py`, `probe*.py` | **Experimental** — protocol/port debugging utilities |

> **Note:** The experimental pairing scripts (`atv_pair.py` etc.) are reference implementations for protocol exploration. They do **not** perform a complete pairing (TLS/M1/M2 verification missing). The working path is `install_kodi.sh` → `plumesign`.

---

## Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `missing port in createListener response` | TV in inconsistent pairing state — re-open *Remote App and Devices* on TV, re-discover port |
| "No pairing service found" after 8 attempts | TV must be on the *Remote App and Devices* screen |
| Install fails despite valid login | Free tier App ID limit (10 IDs / 7 days) — script auto-deletes oldest and retries |
| `plumesign` not found | Place binary at `bin/plumesign` (not committed) |

---

## Project Structure

```
atv-sideload/
├── atvconfig.py              # Config loader
├── install_kodi.sh           # Main install script
├── deb_to_ipa.py             # .deb → .ipa converter
├── config.example.env        # Config template
├── config.env                # Your config (gitignored)
├── .gitignore                # Excludes: bin/, keys/, *.ipa, *.deb, config.env, rp_pairing_file.plist, venv dirs
├── requirements.txt          # Python deps (debug scripts only)
├── bin/plumesign             # Signing tool (not in repo)
├── keys/                     # Pairing keys (gitignored)
├── rp_pairing_file.plist     # Pairing record (gitignored)
├── scan_*.py                 # mDNS/port discovery
├── atv_pair*.py              # Experimental pairing
├── probe*.py                 # Debug utilities
└── docs/
    └── NOTES.md              # Detailed findings & error catalog
```

---

## License

Private project — no license granted.