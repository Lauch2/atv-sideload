#!/usr/bin/env python3
"""Pairt mit dem Apple TV über das Remote-Pairing-Protokoll (manuelles Pairing).

Läuft komplett lokal. Nach dem Pairing wird die Pairing-Datei als
rp_pairing_file.plist gespeichert (das Format, das plumesign/atvloadly brauchen).
"""
import asyncio
import json
import logging
import os
import plistlib
import struct
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from atvconfig import ATV_HOST, ATV_PAIRING_PORT, PAIRING_FILE  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("atvpair")

ATV_PORT = ATV_PAIRING_PORT or 50100
OUT_PATH = str(PAIRING_FILE)

import hashlib


def h(*parts):
    return hashlib.sha256(b"".join(parts)).digest()


def pad(n, length):
    return n.to_bytes(length, "big")


class RemotePairingClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        log.info("[+] Verbunden mit %s:%s", self.host, self.port)

    async def send(self, payload: dict):
        data = plistlib.dumps(payload, fmt=plistlib.FMT_BINARY)
        # Remote-Pairing-Protokoll: 4-Byte-Länge + Payload
        self.writer.write(struct.pack(">I", len(data)) + data)
        await self.writer.drain()

    async def recv(self):
        header = await self.reader.readexactly(4)
        (ln,) = struct.unpack(">I", header)
        body = await self.reader.readexactly(ln)
        return plistlib.loads(body)

    async def pair(self):
        # 1) "Hello"-Handshake
        hello = {
            "message": "Hello",
            "ttl": 30,
            "name": "Hermes-PC",
        }
        await self.send(hello)
        resp = await self.recv()
        log.info("[*] Hello-Antwort: %s", str(resp)[:300])

        # 2) Pairing-Anfrage (Setup)
        setup = {
            "message": "Pairing",
            "state": 1,
            "payload": {},
        }
        await self.send(setup)
        resp = await self.recv()
        log.info("[*] Pairing-Antwort: %s", str(resp)[:300])
        return resp


async def main():
    c = RemotePairingClient(ATV_HOST, ATV_PORT)
    try:
        await c.connect()
        await c.pair()
    except Exception as e:
        log.error("Pairing fehlgeschlagen: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
