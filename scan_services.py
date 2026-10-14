#!/usr/bin/env python3
"""Scannt mDNS nach allen Diensten, die für Apple-TV-Pairing relevant sind."""
import asyncio
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import atvconfig  # noqa: E402,F401  (lädt config.env und setzt vendor-sys.path)

from pymobiledevice3.bonjour import (
    browse_remotepairing,
    browse_remotepairing_manual_pairing,
    browse_remoted,
    browse_mobdev2,
)


async def dump(name, coro):
    try:
        items = await coro
        print(f"\n### {name}: {len(items)} gefunden")
        for it in items:
            print("   hostname:", it.hostname, "| port:", it.port)
            for a in it.addresses:
                print("      addr:", a.full_ip)
            if getattr(it, "properties", None):
                print("      props:", dict(it.properties))
    except Exception as e:
        print(f"\n### {name}: FEHLER {e}")


async def main():
    await dump("_remotepairing._tcp", browse_remotepairing(6))
    await dump("_remotepairing-manual-pairing._tcp", browse_remotepairing_manual_pairing(6))
    await dump("_remoted._tcp", browse_remoted(6))
    await dump("_apple-mobdev2._tcp", browse_mobdev2(6))


asyncio.run(main())
