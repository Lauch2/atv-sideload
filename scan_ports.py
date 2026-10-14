#!/usr/bin/env python3
"""Testet TCP-Verbindungen zu den gefundenen Ports des Apple TV."""
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atvconfig import ATV_HOST as HOST  # noqa: E402

PORTS = [7000, 49152, 62078, 443, 22, 123, 7001]

for p in PORTS:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    try:
        s.connect((HOST, p))
        print(f"Port {p}: OFFEN")
        s.close()
    except Exception as e:
        print(f"Port {p}: zu/gefiltert ({type(e).__name__})")
