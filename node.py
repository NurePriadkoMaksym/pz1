"""HTTP-вузол для обміну транзакціями та блоками."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs
import json, threading
from blockchain import Blockchain
from block import Block
from transaction import Transaction

def request_json(url, method="GET", data=None, timeout=2):
    body = None if data is None else json.dumps(data).encode()
    req = Request(url, data=body, method=method, headers={"Content-Type":"application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as e:
        # Сервер повертає пояснення помилки у JSON, але urllib за замовчуванням
        # показує лише загальний код HTTP. Прочитаємо тіло відповіді.
        raw = e.read()
        try:
            details = json.loads(raw.decode("utf-8")) if raw else {}
            message = details.get("error") or raw.decode("utf-8", errors="replace")
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = raw.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"HTTP {e.code} {e.reason}: {message}"
        ) from e

class Node:
    def __init__(self, port, data, peers=None):
        self.port, self.bc = port, Blockchain(data)
        self.peers = set(p.rstrip("/") for p in (peers or []) if p)
        self.lock = threading.RLock()
    def broadcast(self, path, payload):
        for peer in list(self.peers):
            try: request_json(peer+path, "POST", payload, timeout=1)
            except Exception: pass
    def serve(self):
        node = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args): print("[%s] %s"%(node.port, fmt%args))
            def send(self, code, data):
                raw=json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
                self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def body(self):
                n=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(n) or b"{}")
            def do_GET(self):
                u=urlparse(self.path); q=parse_qs(u.query)
                with node.lock:
                    if u.path=="/status": self.send(200,{"port":node.port,"height":len(node.bc.chain)-1,"peers":sorted(node.peers),"mempool":len(node.bc.mempool)})
                    elif u.path=="/chain": self.send(200,{"chain":node.bc.to_dict()})
                    elif u.path=="/mempool": self.send(200,{"mempool":[t.to_dict() for t in node.bc.mempool]})
                    elif u.path=="/balance": self.send(200,{"address":q.get("address",[""])[0],"balance":node.bc.balance(q.get("address",[""])[0])})
                    else: self.send(404,{"error":"Not found"})
            def do_POST(self):
                try:
                    d=self.body()
                    with node.lock:
                        if self.path=="/transaction":
                            tx=Transaction.from_dict(d); node.bc.add_transaction(tx); result={"accepted":True,"txid":tx.txid}
                            self.send(200,result); threading.Thread(target=node.broadcast,args=("/transaction",tx.to_dict()),daemon=True).start()
                        elif self.path=="/mine":
                            b=node.bc.mine_block(d["miner"]); result={"block":b.to_dict()}
                            self.send(200,result); threading.Thread(target=node.broadcast,args=("/block",b.to_dict()),daemon=True).start()
                        elif self.path=="/block":
                            b=Block.from_dict(d)
                            candidate=node.bc.chain+[b]
                            if b.previous_hash==node.bc.last.hash and node.bc.validate_chain(candidate):
                                node.bc.chain.append(b); node.bc._save(); self.send(200,{"accepted":True})
                            else: self.send(400,{"error":"Invalid block or parent"})
                        elif self.path=="/peers":
                            p=d["url"].rstrip("/"); node.peers.add(p); self.send(200,{"peers":sorted(node.peers)})
                        elif self.path=="/sync":
                            changed=False
                            for p in list(node.peers):
                                try:
                                    remote=request_json(p+"/chain")
                                    chain=[Block.from_dict(x) for x in remote["chain"]]
                                    if node.bc.replace_chain(chain): changed=True
                                    mp=request_json(p+"/mempool").get("mempool",[])
                                    for x in mp:
                                        try: node.bc.add_transaction(Transaction.from_dict(x))
                                        except ValueError: pass
                                except Exception: continue
                            self.send(200,{"changed":changed,"height":len(node.bc.chain)-1})
                        elif self.path=="/chain/replace":
                            chain=[Block.from_dict(x) for x in d["chain"]]
                            ok=node.bc.replace_chain(chain); self.send(200 if ok else 400,{"accepted":ok})
                        else: self.send(404,{"error":"Not found"})
                except Exception as e:
                    self.send(400,{"error":str(e)})
        server=ThreadingHTTPServer(("127.0.0.1",self.port),Handler)
        print(f"Вузол працює: http://127.0.0.1:{self.port}")
        server.serve_forever()
