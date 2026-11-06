"""Детермінована модель транзакції."""
import hashlib, json
from dataclasses import dataclass, asdict
from wallet import Wallet, b64

@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    fee: float
    nonce: int
    public_key: str = ""
    signature: str = ""
    txid: str = ""

    def signing_dict(self):
        return {"sender": self.sender, "recipient": self.recipient,
                "amount": round(float(self.amount), 8), "fee": round(float(self.fee), 8),
                "nonce": int(self.nonce), "public_key": self.public_key}
    def signing_bytes(self):
        return json.dumps(self.signing_dict(), sort_keys=True, separators=(",", ":")).encode()
    def to_dict(self):
        d = asdict(self)
        d["amount"], d["fee"] = round(float(self.amount), 8), round(float(self.fee), 8)
        return d
    @classmethod
    def from_dict(cls, d):
        return cls(**{k:d[k] for k in cls.__dataclass_fields__ if k in d})
    def refresh_id(self):
        d = self.to_dict()
        d["txid"] = ""
        self.txid = hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return self.txid
    @classmethod
    def create(cls, wallet, recipient, amount, fee, nonce):
        tx = cls(wallet.address, recipient, float(amount), float(fee), int(nonce),
                 b64(wallet.public_key), "")
        tx.signature = wallet.sign(tx.signing_bytes())
        tx.refresh_id()
        return tx
    def verify_signature(self):
        if self.sender == "COINBASE":
            return False
        if hashlib.sha256(__import__("base64").b64decode(self.public_key)).hexdigest()[:40] != self.sender:
            return False
        return Wallet.verify(self.public_key, self.signature, self.signing_bytes())
    def valid_shape(self):
        expected = hashlib.sha256(json.dumps(self.to_dict_without_id(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return (self.amount > 0 and self.fee >= 0 and self.nonce >= 0
                and self.sender != self.recipient and bool(self.recipient)
                and expected == self.txid)
    def to_dict_without_id(self):
        d = self.to_dict()
        d["txid"] = ""
        return d
