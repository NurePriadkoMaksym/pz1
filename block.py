"""Блок, дерево Меркла та Proof of Work."""
import hashlib, json, time
from transaction import Transaction

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def merkle_root(transactions):
    if not transactions:
        return hashlib.sha256(b"").hexdigest()
    layer = [hashlib.sha256(canonical(tx.to_dict())).hexdigest() for tx in transactions]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [hashlib.sha256((layer[i] + layer[i+1]).encode()).hexdigest()
                 for i in range(0, len(layer), 2)]
    return layer[0]

class Block:
    def __init__(self, index, timestamp, previous_hash, transactions, difficulty, nonce=0):
        self.index, self.timestamp, self.previous_hash = int(index), float(timestamp), previous_hash
        self.transactions, self.difficulty, self.nonce = transactions, int(difficulty), int(nonce)
        self.merkle_root = merkle_root(transactions)
        self.hash = self.calculate_hash()
    def header_dict(self):
        return {"index":self.index, "timestamp":self.timestamp, "previous_hash":self.previous_hash,
                "merkle_root":self.merkle_root, "difficulty":self.difficulty, "nonce":self.nonce}
    def calculate_hash(self):
        return hashlib.sha256(canonical(self.header_dict())).hexdigest()
    def mine(self):
        target = "0" * self.difficulty
        while True:
            self.hash = self.calculate_hash()
            if self.hash.startswith(target):
                return self.hash
            self.nonce += 1
    def to_dict(self):
        return {**self.header_dict(), "hash":self.hash,
                "transactions":[tx.to_dict() for tx in self.transactions]}
    @classmethod
    def from_dict(cls, d):
        txs = [Transaction.from_dict(x) for x in d["transactions"]]
        b = cls(d["index"], d["timestamp"], d["previous_hash"], txs, d["difficulty"], d["nonce"])
        b.hash = d["hash"]
        return b
