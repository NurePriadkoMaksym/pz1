import base64, hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def unb64(data: str) -> bytes:
    return base64.b64decode(data.encode("ascii"))

class Wallet:
    def __init__(self, private_key: Ed25519PrivateKey):
        self._key = private_key
        self.public_key = self._key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)
        self.address = hashlib.sha256(self.public_key).hexdigest()[:40]

    @classmethod
    def create(cls):
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_file(cls, path):
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(Ed25519PrivateKey.from_private_bytes(unb64(data["private_key"])))

    def save(self, path):
        import json
        raw = self._key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption())
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"private_key": b64(raw), "public_key": b64(self.public_key),
                       "address": self.address}, f, indent=2)
    def sign(self, payload: bytes) -> str:
        return b64(self._key.sign(payload))
    @staticmethod
    def verify(public_key: str, signature: str, payload: bytes) -> bool:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        try:
            Ed25519PublicKey.from_public_bytes(unb64(public_key)).verify(unb64(signature), payload)
            return True
        except Exception:
            return False
