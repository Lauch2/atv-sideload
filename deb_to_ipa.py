#!/usr/bin/env python3
"""Konvertiert ein Kodi-tvOS-.deb in eine .ipa (arbeitet im Repo-Verzeichnis).

Nutzung:
    python3 deb_to_ipa.py [pfad/zum/kodi-tvos.deb] [-o ausgabe.ipa]
"""
import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import lzma
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atvconfig import WORKDIR  # noqa: E402

SRC = WORKDIR / "kodi-deb-extract"
STAGE = WORKDIR / "kodi-ipa-stage"
DEB = Path(os.environ.get("KODI_DEB", "/tmp/kodi-21.3-tvos.deb"))
DST = WORKDIR / "kodi-tvos.ipa"


def extract_deb():
    if os.path.isdir(SRC):
        shutil.rmtree(SRC)
    os.makedirs(SRC, exist_ok=True)

    if not DEB.exists():
        sys.exit(f"FEHLER: {DEB} nicht gefunden (Pfad per KODI_DEB oder Argument setzen)")

    with open(DEB, "rb") as f:
        data = f.read()

    # ar-Archiv parsen
    pos = 8  # "!<arch>\n"
    members = []
    while pos + 60 <= len(data):
        name = data[pos : pos + 16].decode("ascii", "replace").strip()
        size_str = data[pos + 48 : pos + 60].decode("ascii", "replace").strip()
        digits = "".join(ch for ch in size_str if ch.isdigit())
        if not digits:
            break
        size = int(digits)
        body_start = pos + 60
        members.append((name, body_start, size))
        pos = body_start + size + (size % 2)

    data_member = None
    for name, start, size in members:
        if name.startswith("data.tar"):
            data_member = data[start : start + size]
            print(f"[*] data-Member: {name} ({size} Bytes)")
            break
    if data_member is None:
        print("FEHLER: kein data.tar im .deb")
        sys.exit(1)

    if data_member[:6] == b"\xfd7zXZ\x00":
        raw = lzma.decompress(data_member)
    else:
        raw = data_member

    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(SRC)
    print("[*] .deb extrahiert nach", SRC)


def build_ipa():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(os.path.join(STAGE, "Payload"), exist_ok=True)

    apps_dir = os.path.join(SRC, "Applications")
    if not os.path.isdir(apps_dir):
        matches = []
        for root, dirs, files in os.walk(SRC):
            for d in dirs:
                if d.endswith(".app"):
                    matches.append(os.path.join(root, d))
        if not matches:
            print("FEHLER: keine .app gefunden")
            sys.exit(1)
        src_app = matches[0]
    else:
        apps = os.listdir(apps_dir)
        print("Apps im .deb:", apps)
        src_app = os.path.join(apps_dir, apps[0])

    app_name = os.path.basename(src_app)
    dst_app = os.path.join(STAGE, "Payload", app_name)
    print(f"[*] Kopiere {src_app} -> {dst_app}")
    shutil.copytree(src_app, dst_app, symlinks=True)

    if not os.path.exists(os.path.join(dst_app, "Info.plist")):
        print("FEHLER: keine Info.plist")
        sys.exit(1)

    print("[*] Packe IPA...")
    cwd = os.getcwd()
    os.chdir(STAGE)
    try:
        subprocess.run(["zip", "-qr", str(DST), "Payload"], check=True)
    finally:
        os.chdir(cwd)

    size = os.path.getsize(DST) / 1024 / 1024
    print(f"[+] IPA erstellt: {DST} ({size:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Kodi-tvOS-.deb -> .ipa")
    ap.add_argument("deb", nargs="?", type=Path, default=DEB, help="Pfad zum .deb")
    ap.add_argument("-o", "--out", type=Path, default=DST, help="Ziel-.ipa")
    args = ap.parse_args()
    DEB = args.deb
    DST = args.out
    extract_deb()
    build_ipa()
