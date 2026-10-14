#!/usr/bin/env python3
"""Lauscht auf Port 49152 und 62078 des Apple TV (TCP) und prüft,
ob das Gerät dort ein Pairing-Protokoll erwartet (Handshake-Test)."""
import asyncio
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atvconfig import ATV_HOST as HOST  # noqa: E402

PORTS = [49152, 62078]

BANNERS = [b"plist", b"PTAP", b"\x10\x00\x00\x00", b"GATT", b"\x00\x01", b"RP"]

async def try_port(port):
    print(f"\n=== Port {port} ===")
    try:
        r, w = await asyncio.open_connection(HOST, port)
        print(f"[+] verbunden mit {HOST}:{port}")
        # Erst passiv lauschen, was das Gerät sendet
        try:
            data = await asyncio.wait_for(r.read(64), timeout=4)
            if data:
                print(f"[*] Gerät sendet zuerst: {data[:40]!r}")
            else:
                print("[*] Gerät sendet nichts (EOF)")
        except asyncio.TimeoutError:
            print("[*] Gerät sendet nichts (Timeout 4s)")
            # Nun aktiv einen plist-Handshake versuchen
            import plistlib, struct
            body = plistlib.dumps(
                {"type": "pair-setup", "state": 1, "pairingData": {"method": "pin"}},
                fmt=plistlib.FMT_BINARY,
            )
            w.write(b"plist" + struct.pack(">I", len(body)) + body)
            await w.drain()
            try:
                data = await asyncio.wait_for(r.read(128), timeout=5)
                print(f"[*] Antwort auf plist: {data[:60]!r}")
            except asyncio.TimeoutError:
                print("[*] Keine Antwort auf plist (Timeout)")
        w.close()
    except Exception as e:
        print(f"[!] Fehler: {type(e).__name__}: {e}")

async def main():
    for p in PORTS:
        await try_port(p)

asyncio.run(main())
