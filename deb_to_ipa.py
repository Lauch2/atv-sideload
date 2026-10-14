#!/usr/bin/env python3
"""Convert a tvOS .deb to a .ipa (works in repo directory).

Usage:
    python3 deb_to_ipa.py [path/to/app-tvos.deb] [-o output.ipa]
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

SRC = WORKDIR / "app-deb-extract"
STAGE = WORKDIR / "app-ipa-stage"
DEB = Path(os.environ.get("APP_DEB", "/tmp/app-tvos.deb"))
DST = WORKDIR / "app-tvos.ipa"


def extract_deb():
    if os.path.isdir(SRC):
        shutil.rmtree(SRC)
    os.makedirs(SRC, exist_ok=True)

    if not DEB.exists():
        sys.exit(f"ERROR: {DEB} not found (set APP_DEB env var or pass as argument)")

    with open(DEB, "rb") as f:
        data = f.read()

    # Parse ar archive
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
            print(f"[*] data member: {name} ({size} bytes)")
            break
    if data_member is None:
        print("ERROR: no data.tar in .deb")
        sys.exit(1)

    if data_member[:6] == b"\xfd7zXZ\x00":
        raw = lzma.decompress(data_member)
    else:
        raw = data_member

    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(SRC)
    print("[*] .deb extracted to", SRC)


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
            print("ERROR: no .app found")
            sys.exit(1)
        src_app = matches[0]
    else:
        apps = os.listdir(apps_dir)
        print("Apps in .deb:", apps)
        src_app = os.path.join(apps_dir, apps[0])

    app_name = os.path.basename(src_app)
    dst_app = os.path.join(STAGE, "Payload", app_name)
    print(f"[*] Copy {src_app} -> {dst_app}")
    shutil.copytree(src_app, dst_app, symlinks=True)

    if not os.path.exists(os.path.join(dst_app, "Info.plist")):
        print("ERROR: no Info.plist")
        sys.exit(1)

    print("[*] Packing IPA...")
    cwd = os.getcwd()
    os.chdir(STAGE)
    try:
        subprocess.run(["zip", "-qr", str(DST), "Payload"], check=True)
    finally:
        os.chdir(cwd)

    size = os.path.getsize(DST) / 1024 / 1024
    print(f"[+] IPA created: {DST} ({size:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="tvOS .deb -> .ipa")
    ap.add_argument("deb", nargs="?", type=Path, default=DEB, help="Path to .deb")
    ap.add_argument("-o", "--out", type=Path, default=DST, help="Output .ipa")
    args = ap.parse_args()
    DEB = args.deb
    DST = args.out
    extract_deb()
    build_ipa()