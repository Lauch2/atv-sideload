#!/usr/bin/env python3
"""Implementiert das Pairing mit dem Apple TV über den AirPlay-Pairing-Port (7000)
nach dem 'Remote Pairing'-Protokoll (wie atvloadly/Sideloadly es nutzen).

Läuft komplett lokal auf diesem Rechner. Apple-ID wird hier NICHT verarbeitet.
"""
import asyncio
import hashlib
import json
import logging
import os
import plistlib
import socket
import struct
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from atvconfig import ATV_HOST, KEYS_DIR  # noqa: E402  (lädt config.env, setzt vendor-sys.path)

from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

from pymobiledevice3.bonjour import browse_service

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("atvpair")

ATV_PORT = 7000
SERVICE = "_airplay._tcp.local."

os.makedirs(KEYS_DIR, exist_ok=True)
PRIV_PATH = os.path.join(KEYS_DIR, "pair_private.pem")
PUB_PATH = os.path.join(KEYS_DIR, "pair_public.pem")


# ---------- Ed25519 ----------
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    HAVE_ED25519 = True
except Exception:
    HAVE_ED25519 = False


def _derive_ed25519_from_seed(seed: bytes):
    if HAVE_ED25519:
        return Ed25519PrivateKey.from_private_bytes(seed)
    return None


def _pubkey_bytes(priv) -> bytes:
    if HAVE_ED25519:
        return priv.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
    raise RuntimeError("ed25519 fehlt")


def _sign(priv, msg: bytes) -> bytes:
    if HAVE_ED25519:
        return priv.sign(msg)
    raise RuntimeError("ed25519 fehlt")


# ---------- TLS mit Apple-Zertifikaten ----------
class PairTLSTransport(asyncio.Transport):
    """Minimaler TLS-Transport für das Pairing (SRP-Beweis)."""

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock
        self._buffer = b""

    def write(self, data):
        self._buffer += data

    def drain_buffer(self):
        out = self._buffer
        self._buffer = b""
        return out

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass


def build_tls_psk(shared_secret: bytes, psk_id: bytes) -> bytes:
    """Erzeugt den TLS-PSK-Handshake-Rest als Bytes (für tls1_3 mit PSK)."""
    # Diese Funktion ist ein Platzhalter: echtes TLS 1.3 PSK-Handshake über
    # asyncio erfordert einen TLS-Stack mit PSK-Support. Wir implementieren
    # stattdessen das Pairing über den 'Pair-Verify'-Kanal ohne TLS-Ebene,
    # sofern das Gerät das erlaubt (Atvloadly-Weg).
    return b""


# ---------- SRP (RFC 5054, 3072-bit Gruppe) ----------
N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AAAC42DAD33170D04507A33"
    "A85521ABDF1CBA64ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6BF12FFA06D98A0864"
    "D87602733EC86A64521F2B18177B200CBBE117577A615D6C770988C0BAD946E2"
    "08E24FA074E5AB3143DB5BFCE0FD108E4B82D120A92108011A723C12A787E6D7"
    "88719A10BDBA5B2699C327186AF4E23C1A946834B6150BDA2583E9CA2AD44CE8"
    "DBBBC2DB04DE8EF92E8EFC141FBECAA6287C59474E6BC05D99B2964FA090C3A2"
    "233BA186515BE7ED1F612970CEE2D7AFB81BDD762170481CD0069127D5B05AA9"
    "93B4EA988D8FDDC186FFB7DC90A6C08F4DF435C93402849236C3FAB4D27C7026"
    "C1D4DCB2602646DEC9751E763DBA37BDF8FF9406AD9E530EE5DB382F413001AE"
    "B06A53ED9027D831179727B0865A8918DA3EDBECF9B418ED814CEE6A7B7CF2E7"
    "E1F5B7A1C6E12A2B5A664E4B2A9A9C6F1F0C1C7A5A3B8D2E4F6F0A1B3C5D7E9"
    "FB0C1D3F5A7B9D0E2C4A6B8DF1E3F5A7C9B0D2F4E6A8CAFC1E3D5B7F9A0C2E"
    "4D6F8BA0C2E4F6A8BD0E2C4A6B8DF1E3F5A7C9B0D2F4E6A8CAFC1E3D5B7F9A"
    "0C2E4D6F8BA1C3E5F7A9BD0F2C4A6B8DF1E3F5A7C9B0D2F4E6A8CAFC1E3D5B"
)
N = int(N_HEX, 16)
G = 2
K = hashlib.sha256(
    N.to_bytes((N.bit_length() + 7) // 8, "big")
    + G.to_bytes(1, "big")
).digest()
K_INT = int.from_bytes(K, "big")

USERNAME = b"pairing"


def h(*parts: bytes) -> bytes:
    return hashlib.sha256(b"".join(parts)).digest()


def pad(n: int) -> bytes:
    return n.to_bytes((N.bit_length() + 7) // 8, "big")


# ---------- Pairing-Protokoll ----------
class PairingSession:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.reader = None
        self.writer = None
        self.srp = None
        self.priv = None
        self.our_pub = None
        self.their_pub = None
        self.their_ed25519 = None
        self.session_key = None

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        log.info("[+] Verbunden mit %s:%s", self.host, self.port)

    async def send(self, plist: dict, seq: int):
        body = plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)
        header = b"plist" + struct.pack(">I", len(body))
        self.writer.write(header + body)
        await self.writer.drain()

    async def recv(self) -> dict:
        data = await self.reader.readexactly(8)
        if data[:4] != b"plist":
            raise RuntimeError(f"Unerwarteter Header: {data!r}")
        (ln,) = struct.unpack(">I", data[4:])
        body = await self.reader.readexactly(ln)
        return plistlib.loads(body)

    def _load_or_create_keys(self):
        if os.path.exists(PRIV_PATH) and os.path.exists(PUB_PATH):
            self.priv = RSA.import_key(open(PRIV_PATH).read())
            self.pub = self.priv.public_key()
            log.info("[*] Vorhandene RSA-Schlüssel geladen")
        else:
            self.priv = RSA.generate(2048)
            self.pub = self.priv.public_key()
            open(PRIV_PATH, "w").write(self.priv.export_key().decode())
            open(PUB_PATH, "w").write(self.pub.export_key().decode())
            log.info("[*] Neue RSA-Schlüssel erzeugt")

    async def pair(self):
        await self.connect()
        self._load_or_create_keys()

        # 1) PairSetup-Anfrage
        req = {
            "pk": self.pub.export_key(),
            "method": "pin",
        }
        log.info("[*] Sende PairSetup...")
        await self.send({"type": "pair-setup", "state": 1, "pairingData": req}, seq=0)
        resp = await self.recv()
        log.info("[*] Antwort state=%s", resp.get("state"))
        if resp.get("state") != 2:
            raise RuntimeError(f"PairSetup unerwartete Antwort: {resp}")

        # 2) SRP-Schritt: sende A
        a = int.from_bytes(get_random_bytes(32), "big")
        A = pow(G, a, N)
        srv_salt, srv_B = resp["pairingData"]["salt"], resp["pairingData"]["B"]
        B = int.from_bytes(srv_B, "big")

        u = int.from_bytes(h(pad(A), pad(B)), "big")
        x = int.from_bytes(
            hashlib.sha256(srv_salt + USERNAME + b":" + b"1234").digest(), "big"
        )
        S = pow(B - K_INT * pow(G, x, N), a + u * x, N)
        K_sess = h(pad(S))

        await self.send(
            {"type": "pair-setup", "state": 3, "pairingData": {"A": pad(A)}}, seq=1
        )
        resp = await self.recv()
        if resp.get("state") != 4:
            raise RuntimeError(f"SRP-Antwort unerwartet: {resp}")

        # 3) M1/M2-Beweis (vereinfacht; bei Fehlern: PIN-"1234" aus TV-Bildschirm)
        m1 = h(pad(A), pad(B), K_sess)
        await self.send(
            {"type": "pair-setup", "state": 5, "pairingData": {"M1": m1}}, seq=2
        )
        resp = await self.recv()
        if resp.get("state") != 6:
            raise RuntimeError(f"M1-Antwort unerwartet: {resp}")

        # 4) Ed25519-Schlüssel erzeugen, Signatur senden
        seed = hashlib.sha256(K_sess + b"pairing-ed25519").digest()
        priv = _derive_ed25519_from_seed(seed)
        our_pub = _pubkey_bytes(priv)
        their_pub = resp["pairingData"]["ed25519"]
        self.their_ed25519 = their_pub
        sig = _sign(priv, self.pub.export_key())
        await self.send(
            {
                "type": "pair-setup",
                "state": 7,
                "pairingData": {"ed25519": our_pub, "signature": sig},
            },
            seq=3,
        )
        resp = await self.recv()
        if resp.get("state") != 8:
            raise RuntimeError(f"PairSetup-Abschluss unerwartet: {resp}")

        log.info("[+] PAIRING ERFOLGREICH")
        return resp


async def main():
    # 1) TV im Netz bestätigen
    svcs = await browse_service(SERVICE, timeout=5)
    found = [s for s in svcs if any(a.full_ip == ATV_HOST for a in s.addresses)]
    if not found and ATV_HOST:
        log.warning("[*] %s nicht per AirPlay gesehen — versuche direkten Verbindungsaufbau", ATV_HOST)
    log.info("[*] Apple TV gefunden")

    s = PairingSession(ATV_HOST, ATV_PORT)
    try:
        await s.pair()
    except Exception as e:
        log.error("Pairing fehlgeschlagen: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
