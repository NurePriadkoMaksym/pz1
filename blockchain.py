"""Логіка навчального блокчейну: мемпул, баланс, PoW і перевірка."""
import json, os, time, hashlib
from block import Block, canonical
from transaction import Transaction

REWARD = 50.0
TARGET_BLOCK_SECONDS = 10.0
RETARGET_INTERVAL = 5
MAX_DIFFICULTY = 5

class Blockchain:
    def __init__(self, path=None, difficulty=2):
        self.path = path
        self.initial_difficulty = difficulty
        self.mempool = []
        self.peers = set()
        if path and os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f: data = json.load(f)
                self.chain = [Block.from_dict(x) for x in data["chain"]]
                self.initial_difficulty = data.get("initial_difficulty", difficulty)
                if not self.validate_chain(self.chain): raise ValueError("Invalid stored chain")
            except Exception:
                self.chain = [self._genesis()]
        else:
            self.chain = [self._genesis()]
        self._save()
    def _genesis(self):
        b = Block(0, 1700000000.0, "0"*64, [], self.initial_difficulty, 0)
        b.mine()
        return b
    @property
    def last(self): return self.chain[-1]
    def _save(self):
        if self.path:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"initial_difficulty":self.initial_difficulty,
                           "chain":[b.to_dict() for b in self.chain]}, f, indent=2)
    def balance(self, address, chain=None):
        bal = 0.0
        for block in (chain or self.chain):
            for tx in block.transactions:
                if tx.sender == "COINBASE" and tx.recipient == address: bal += tx.amount
                else:
                    if tx.sender == address: bal -= tx.amount + tx.fee
                    if tx.recipient == address: bal += tx.amount
        return round(bal, 8)
    def next_nonce(self, address, chain=None):
        used = [tx.nonce for b in (chain or self.chain) for tx in b.transactions
                if tx.sender == address and tx.sender != "COINBASE"]
        used += [tx.nonce for tx in self.mempool if tx.sender == address]
        return max(used, default=-1) + 1
    def _spent_pending(self, address):
        return sum(tx.amount + tx.fee for tx in self.mempool if tx.sender == address)
    def add_transaction(self, tx):
        if not tx.valid_shape(): raise ValueError("Некоректні поля або txid")
        if not tx.verify_signature(): raise ValueError("Недійсний цифровий підпис")
        if any(t.txid == tx.txid for t in self.mempool) or any(
            t.txid == tx.txid for b in self.chain for t in b.transactions):
            raise ValueError("Дублікат транзакції")
        if tx.nonce != self.next_nonce(tx.sender): raise ValueError("Неправильний nonce")
        if self.balance(tx.sender) - self._spent_pending(tx.sender) < tx.amount + tx.fee:
            raise ValueError("Недостатньо коштів")
        self.mempool.append(tx)
        return True
    def expected_difficulty(self, chain=None):
        c = chain or self.chain
        if len(c) <= 1 or (len(c)-1) % RETARGET_INTERVAL:
            return c[-1].difficulty
        old = c[-(RETARGET_INTERVAL+1)]
        elapsed = max(0.001, c[-1].timestamp - old.timestamp)
        expected = RETARGET_INTERVAL * TARGET_BLOCK_SECONDS
        d = c[-1].difficulty
        if elapsed < expected / 2: d += 1
        elif elapsed > expected * 2: d -= 1
        return max(1, min(MAX_DIFFICULTY, d))
    def mine_block(self, miner):
        included = []
        pending = sorted(self.mempool, key=lambda t:(t.sender,t.nonce))
        available = {}
        for tx in pending:
            bal = available.get(tx.sender, self.balance(tx.sender))
            expected = self.next_nonce(tx.sender, self.chain) + sum(1 for x in included if x.sender == tx.sender)
            if tx.nonce == expected and bal >= tx.amount + tx.fee:
                included.append(tx); available[tx.sender] = bal - tx.amount - tx.fee
        fees = round(sum(t.fee for t in included), 8)
        coinbase = Transaction("COINBASE", miner, REWARD + fees, 0, len(self.chain))
        coinbase.txid = coinbase.refresh_id()
        txs = [coinbase] + included
        b = Block(len(self.chain), time.time(), self.last.hash, txs, self.expected_difficulty())
        b.mine()
        self.chain.append(b)
        self.mempool = [t for t in self.mempool if t not in included]
        self._save()
        return b
    def validate_chain(self, chain=None):
        c = chain or self.chain
        if not c or c[0].index != 0 or c[0].previous_hash != "0"*64: return False
        if c[0].transactions or c[0].merkle_root != merkle_root_safe([]): return False
        for i,b in enumerate(c):
            if b.hash != b.calculate_hash() or not b.hash.startswith("0"*b.difficulty): return False
            if b.merkle_root != __import__("block").merkle_root(b.transactions): return False
            if i and (b.index != i or b.previous_hash != c[i-1].hash): return False
            if i == 0: continue
            if not b.transactions or b.transactions[0].sender != "COINBASE": return False
            fees = 0.0
            temp = c[:i]
            seen = set()
            for tx in b.transactions[1:]:
                if not tx.valid_shape() or not tx.verify_signature(): return False
                if tx.txid in seen: return False
                seen.add(tx.txid)
                if tx.nonce != self.next_nonce_for_chain(tx.sender, temp): return False
                if self.balance(tx.sender, temp) < tx.amount + tx.fee: return False
                fees += tx.fee
                # Build prefix with this transaction for subsequent spends in the same block.
                temp = temp + [Block(999, b.timestamp, "0"*64, [tx], 1, 0)]
            cb = b.transactions[0]
            if cb.amount > REWARD + fees + 1e-8 or cb.amount < 0 or cb.fee != 0: return False
        return True
    def next_nonce_for_chain(self, address, chain):
        return max([tx.nonce for b in chain for tx in b.transactions
                    if tx.sender == address and tx.sender != "COINBASE"], default=-1)+1
    def replace_chain(self, candidate):
        if not self.validate_chain(candidate): return False
        work = lambda c: sum(16**b.difficulty for b in c[1:])
        if work(candidate) <= work(self.chain): return False
        new_ids = {tx.txid for b in candidate for tx in b.transactions}
        orphaned = [tx for b in self.chain[1:] for tx in b.transactions[1:]
                    if tx.txid not in new_ids]
        self.chain = candidate
        for tx in orphaned:
            try: self.add_transaction(tx)
            except ValueError: pass
        self._save()
        return True
    def to_dict(self): return [b.to_dict() for b in self.chain]

def merkle_root_safe(txs):
    from block import merkle_root
    return merkle_root(txs)
