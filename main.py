import argparse, json, time, urllib.request
from wallet import Wallet
from transaction import Transaction
from node import Node, request_json
from experiment import run_experiment

def call(url, path, method="GET", data=None):
    try:
        return request_json(url.rstrip("/") + path, method, data, timeout=60)
    except RuntimeError as e:
        # Показуємо повідомлення вузла без довгого traceback.
        raise SystemExit(str(e)) from e

def main():
    p=argparse.ArgumentParser(description="Навчальний блокчейн")
    sub=p.add_subparsers(dest="cmd",required=True)
    w=sub.add_parser("wallet"); w.add_argument("--output",default="wallet.json")
    n=sub.add_parser("node"); n.add_argument("--port",type=int,required=True); n.add_argument("--data",default="node.json"); n.add_argument("--peers",default="")
    for name in ("status","chain","sync","validate"):
        x=sub.add_parser(name); x.add_argument("--url",default="http://127.0.0.1:8001")
    b=sub.add_parser("balance"); b.add_argument("address"); b.add_argument("--url",default="http://127.0.0.1:8001")
    m=sub.add_parser("mine"); m.add_argument("--miner",required=True); m.add_argument("--url",default="http://127.0.0.1:8001")
    s=sub.add_parser("send"); s.add_argument("--wallet",required=True); s.add_argument("--to",required=True); s.add_argument("--amount",type=float,required=True); s.add_argument("--fee",type=float,default=0.1); s.add_argument("--url",default="http://127.0.0.1:8001")
    e=sub.add_parser("experiment"); e.add_argument("--runs",type=int,default=10); e.add_argument("--difficulties",default="1,2,3,4"); e.add_argument("--output",default="mining_experiment.png")
    args=p.parse_args()
    if args.cmd=="wallet":
        wallet=Wallet.create(); wallet.save(args.output); print("Адреса:",wallet.address); print("Гаманець збережено:",args.output)
    elif args.cmd=="node": Node(args.port,args.data,args.peers.split(",")).serve()
    elif args.cmd=="status": print(json.dumps(call(args.url,"/status"),indent=2,ensure_ascii=False))
    elif args.cmd=="chain": print(json.dumps(call(args.url,"/chain"),indent=2,ensure_ascii=False))
    elif args.cmd=="balance": print(call(args.url,"/balance?address="+args.address))
    elif args.cmd=="mine": print(json.dumps(call(args.url,"/mine","POST",{"miner":args.miner}),indent=2,ensure_ascii=False))
    elif args.cmd=="sync": print(call(args.url,"/sync","POST",{}))
    elif args.cmd=="validate":
        d=call(args.url,"/chain"); from block import Block
        from blockchain import Blockchain
        bc=Blockchain(); chain=[Block.from_dict(x) for x in d["chain"]]
        print("Ланцюг коректний" if bc.validate_chain(chain) else "ПОМИЛКА: ланцюг некоректний")
    elif args.cmd=="send":
        wallet=Wallet.from_file(args.wallet); status=call(args.url,"/status")
        # Nonce береться з підтвердженого ланцюга; для кількох паралельних транзакцій синхронізуйте вузол.
        from block import Block
        from blockchain import Blockchain
        chain=[Block.from_dict(x) for x in call(args.url,"/chain")["chain"]]
        bc=Blockchain(); bc.chain=chain
        nonce=bc.next_nonce(wallet.address)
        tx=Transaction.create(wallet,args.to,args.amount,args.fee,nonce)
        print(call(args.url,"/transaction","POST",tx.to_dict()))
    elif args.cmd=="experiment": run_experiment([int(x) for x in args.difficulties.split(",")],args.runs,args.output)

if __name__=="__main__": main()
