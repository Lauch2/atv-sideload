#!/usr/bin/env python3
"""Scannt alle für StikPair/Xcode relevanten mDNS-Dienste des Apple TV."""
import asyncio
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from atvconfig import ATV_HOST as ATV_IP  # noqa: E402

from pymobiledevice3.bonjour import (
    browse_remotepairing,
    browse_remotepairing_manual_pairing,
    browse_remoted,
    browse_mobdev2,
    browse_service,
)


def show(items):
    # /24 des konfigurierten TV als "eigenes Netz" ansehen
    subnet = ".".join(ATV_IP.split(".")[:3]) + "." if ATV_IP.count(".") == 3 else None
    found = []
    for it in items:
        addrs = [a.full_ip for a in it.addresses]
        hit = ATV_IP in addrs or (
            subnet is not None and any(a.startswith(subnet) and a != ATV_IP for a in addrs)
        )
        props = dict(it.properties) if getattr(it, "properties", None) else {}
        name = getattr(it, "host", "") or it.hostname
        found.append((name, it.port, addrs, props))
    return found


async def dump(label, coro):
    try:
        items = await coro
        rows = show(items)
        print(f"### {label}: {len(items)} Einträge")
        for name, port, addrs, props in rows:
            print(f"   host={name} port={port} addrs={addrs}")
            if props:
                print(f"       props={props}")
    except Exception as e:
        print(f"### {label}: FEHLER {e}")


async def main():
    await dump("_remotepairing._tcp", browse_remotepairing(6))
    await dump("_remotepairing-manual-pairing._tcp", browse_remotepairing_manual_pairing(6))
    await dump("_remoted._tcp", browse_remoted(6))
    await dump("_apple-mobdev2._tcp", browse_mobdev2(6))
    await dump("_appletv-v2._tcp", browse_service("_appletv-v2._tcp.local.", 6))
    await dump("_companion-link._tcp", browse_service("_companion-link._tcp.local.", 6))


asyncio.run(main())
