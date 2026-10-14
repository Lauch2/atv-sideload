#!/usr/bin/env python3
"""Zentrale Konfiguration für die Apple-TV-Sideload-Skripte.

Liest Werte in dieser Reihenfolge: echte Umgebungsvariablen > ``config.env``
(nicht im Repo) > ``.env`` > Standardwerte. Damit stehen keine IP-Adressen,
UDIDs, Team-IDs oder Schlüsselpfade im Repository.

Verwendung::

    from atvconfig import ATV_HOST, TEAM_ID, PLUMESIGN
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_env_file(path: Path) -> None:
    """Minimaler KEY=VALUE-Parser; vorhandene Umgebungsvariablen gewinnen."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


for _candidate in ("config.env", ".env"):
    _load_env_file(ROOT / _candidate)


def get(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or default


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Fehlende Konfiguration: {name}\n"
            f"  Bitte 'config.env' anlegen (Vorlage: config.example.env)."
        )
    return value


def path(name: str, default: str) -> Path:
    """Pfad aus der Konfiguration, relativ zum Repo-Verzeichnis aufgelöst."""
    raw = get(name, default) or default
    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else (ROOT / candidate)


# --- Apple TV ---
ATV_HOST = get("ATV_HOST", "appletv.local")
ATV_UDID = get("ATV_UDID", "")
ATV_PAIRING_PORT = int(get("ATV_PAIRING_PORT") or 0)

# --- Signierung ---
TEAM_ID = get("TEAM_ID", "")
BUNDLE_ID = get("BUNDLE_ID", "")
APPLE_ID = get("APPLE_ID", "")

# --- Pfade ---
PLUMESIGN = path("PLUMESIGN", "bin/plumesign")
PAIRING_FILE = path("PAIRING_FILE", "rp_pairing_file.plist")
KEYS_DIR = path("KEYS_DIR", "keys")
WORKDIR = path("WORKDIR", ".")
IPA = path("IPA", "app-tvos.ipa")

# --- Vendor-Site-Packages (venv im Repo, siehe README) ---
VENDOR_SITE = path(
    "VENDOR_SITE",
    f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages",
)
if VENDOR_SITE.is_dir() and str(VENDOR_SITE) not in sys.path:
    sys.path.insert(0, str(VENDOR_SITE))


if __name__ == "__main__":
    print(f"ROOT         = {ROOT}")
    print(f"ATV_HOST     = {ATV_HOST}")
    print(f"ATV_UDID     = {ATV_UDID or '(nicht gesetzt)'}")
    print(f"TEAM_ID      = {TEAM_ID or '(nicht gesetzt)'}")
    print(f"APPLE_ID     = {APPLE_ID or '(nicht gesetzt)'}")
    print(f"PLUMESIGN    = {PLUMESIGN}")
    print(f"PAIRING_FILE = {PAIRING_FILE}  (vorhanden: {PAIRING_FILE.exists()})")
    print(f"VENDOR_SITE  = {VENDOR_SITE}  (vorhanden: {VENDOR_SITE.is_dir()})")
