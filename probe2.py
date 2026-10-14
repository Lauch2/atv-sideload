#!/usr/bin/env python3
"""Prüft, ob Port 49152/62078 des Apple TV einen anderen Handshake erwartet:
- Bluetooth-Pairing-Frame (RP = Rapport)
- TLSServer-Handshake (ClientHello) als Test
- roher plist (bereits versucht)
"""
import asyncio
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atvconfig import ATV_HOST as HOST  # noqa: E402

PORT = 49152


async def send_raw(data, label, read_len=128, timeout=5):
    try:
        r, w = await asyncio.open_connection(HOST, PORT)
        print(f"[*] {label}: sende {len(data)} Bytes")
        w.write(data)
        await w.drain()
        try:
            resp = await asyncio.wait_for(r.read(read_len), timeout=timeout)
            print(f"[*] {label}: Antwort {len(resp)} Bytes: {resp[:60]!r}")
        except asyncio.TimeoutError:
            print(f"[*] {label}: keine Antwort (Timeout {timeout}s)")
        w.close()
    except Exception as e:
        print(f"[!] {label}: {type(e).__name__}: {e}")


async def main():
    # 1) Bluetooth-artiger Pairing-Frame (RP-Handshake)
    #    Rapport nutzt: 0x00 0x00 0x00 0x00 + opcode
    await send_raw(b"\x00\x00\x00\x00\x10\x00\x00\x00\x01", "RP-Frame")

    # 2) TLS ClientHello (leerer, minimaler Handshake)
    client_hello = bytes.fromhex(
        "16030100c0010000bc0303" + "00" * 32 + "00000000000000000000000000000000"
        "00000000000000000000000000000000" + "0000" + "0008" + "0013001200020003"
        "0000" + "0000" + "0000"
    )
    await send_raw(client_hello, "TLS-ClientHello")

    # 3) Einfacher TCP-Banner-Grab
    await send_raw(b"", "Banner-Grab", read_len=64, timeout=3)


asyncio.run(main())
