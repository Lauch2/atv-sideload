#!/usr/bin/env python3
"""Ermittelt die pi-ID (Pairing-Identifier) des Apple TV aus den AirPlay-mDNS-Daten."""
import re
import subprocess

out = subprocess.run(
    ["avahi-browse", "-rt", "_airplay._tcp"], capture_output=True, text=True, timeout=15
).stdout

pis = sorted(set(re.findall(r"pi=([0-9A-Fa-f-]{20,})", out)))
if pis:
    print("PI-IDs gefunden:")
    for p in pis:
        print(" ", p)
else:
    print("Keine pi-ID gefunden. Volle TXT-Daten:")
    for line in out.splitlines():
        if "txt =" in line or "hostname" in line or "address" in line:
            print(line)
