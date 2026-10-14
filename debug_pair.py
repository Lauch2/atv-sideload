#!/usr/bin/env python3
"""Debug-Skript: sendet ein PairSetup und zeigt die rohe Antwort des Apple TV,
ohne Annahmen über das Protokoll zu treffen."""
import asyncio
import plistlib
import socket
import struct
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from atvconfig import ATV_HOST as HOST  # noqa: E402

PORT = 7000


async def main():
    r, w = await asyncio.open_connection(HOST, PORT)
    print("[+] verbunden")
    for seq, body in [
        (0, {"type": "pair-setup", "state": 1, "pairingData": {"method": "pin"}}),
    ]:
        data = plistlib.dumps(body, fmt=plistlib.FMT_BINARY)
        w.write(b"plist" + struct.pack(">I", len(data)) + data)
        await w.drain()
        print(f"[*] gesendet seq={seq}")
    # Antwort mit Timeout lesen
    try:
        raw = await asyncio.wait_for(r.read(65536), timeout=10)
        print("[*] Antwortbytes:", len(raw))
        if raw[:4] == b"plist":
            ln = struct.unpack(">I", raw[4:8])[0]
            payload = raw[8 : 8 + ln]
            print("[*] Plist-Länge:", ln)
            try:
                obj = plistlib.loads(payload)
                print("[*] Objekt:", obj)
            except Exception as e:
                print("[!] Plist-Parse-Fehler:", e)
                print("[!] Rohbytes:", payload[:500])
        else:
            print("[!] Kein plist-Header, erste Bytes:", raw[:60])
    except asyncio.TimeoutError:
        print("[!] KEINE ANTWORT (Timeout 10s) — TV hat die Verbindung evtl. geschlossen")


asyncio.run(main())
