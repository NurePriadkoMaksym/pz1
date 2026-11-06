import sys, os, unittest, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from wallet import Wallet
from transaction import Transaction
from block import Block, merkle_root
from blockchain import Blockchain

class BlockchainTests(unittest.TestCase):
    def setUp(self):
        self.bc=Blockchain(difficulty=1)
        self.miner=Wallet.create()
        self.alice=Wallet.create()
        self.bob=Wallet.create()
        self.bc.chain.append(self.bc.mine_block(self.miner.address)) if False else None
        self.bc.mine_block(self.miner.address)
    def tx(self, wallet, recipient, amount=1, fee=.1, nonce=None):
        if nonce is None: nonce=self.bc.next_nonce(wallet.address)
        return Transaction.create(wallet,recipient,amount,fee,nonce)
    def test_genesis_exists(self): self.assertEqual(self.bc.chain[0].index,0)
    def test_genesis_hash_valid(self): self.assertEqual(self.bc.chain[0].hash,self.bc.chain[0].calculate_hash())
    def test_merkle_empty(self): self.assertEqual(merkle_root([]),Block(0,1,"0",[],1).merkle_root)
    def test_merkle_odd_count(self):
        txs=[self.tx(self.miner, self.alice.address, .2, 0, i) for i in range(1,4)]
        self.assertTrue(merkle_root(txs))
    def test_merkle_even_odd_differ(self):
        a=[self.tx(self.miner,self.alice.address,.2,0,i) for i in range(1,4)]
        self.assertNotEqual(merkle_root(a),merkle_root(a[:2]))
    def test_signature_valid(self):
        t=self.tx(self.miner,self.alice.address); self.assertTrue(t.verify_signature())
    def test_tampered_signature_payload_rejected(self):
        t=self.tx(self.miner,self.alice.address); t.amount+=1
        self.assertFalse(t.verify_signature())
    def test_transaction_accepted_after_funding(self):
        t=self.tx(self.miner,self.alice.address,1,.1,0)
        self.assertTrue(self.bc.add_transaction(t))
    def test_duplicate_mempool_rejected(self):
        t=self.tx(self.miner,self.alice.address,1,.1,0); self.bc.add_transaction(t)
        with self.assertRaises(ValueError): self.bc.add_transaction(t)
    def test_insufficient_funds_rejected(self):
        t=self.tx(self.alice,self.bob.address,999,0,0)
        with self.assertRaises(ValueError): self.bc.add_transaction(t)
    def test_wrong_nonce_rejected(self):
        t=self.tx(self.miner,self.alice.address,1,.1,99)
        with self.assertRaises(ValueError): self.bc.add_transaction(t)
    def test_pow_prefix(self):
        b=Block(1,time.time(),"0"*64,[],2); b.mine()
        self.assertTrue(b.hash.startswith("00"))
    def test_chain_valid(self): self.assertTrue(self.bc.validate_chain())
    def test_tamper_block_detected(self):
        old=self.bc.chain[1].transactions[0].amount
        self.bc.chain[1].transactions[0].amount=old+5
        self.assertFalse(self.bc.validate_chain())
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            path=os.path.join(d,"chain.json"); bc=Blockchain(path,difficulty=1); bc.mine_block(self.miner.address)
            loaded=Blockchain(path); self.assertEqual(len(loaded.chain),2); self.assertTrue(loaded.validate_chain())
    def test_confirmed_tx_replay_rejected(self):
        t=self.tx(self.miner,self.alice.address,1,.1,0); self.bc.add_transaction(t); self.bc.mine_block(self.miner.address)
        with self.assertRaises(ValueError): self.bc.add_transaction(t)

if __name__=="__main__": unittest.main()
