```bash
python -m venv .venv
.venv\Scripts\activate

source .venv/bin/activate
pip install -r requirements.txt
```

Запуск вузлів 
```bash
python main.py node --port 8001 --data node1.json --peers http://127.0.0.1:8002,http://127.0.0.1:8003
python main.py node --port 8002 --data node2.json --peers http://127.0.0.1:8001,http://127.0.0.1:8003
python main.py node --port 8003 --data node3.json --peers http://127.0.0.1:8001,http://127.0.0.1:8002
```

Виконання команд
```bash
python main.py wallet
python main.py status --url http://127.0.0.1:8001
python main.py chain --url http://127.0.0.1:8001
python main.py balance [ADDRESS] --url http://127.0.0.1:8001
python main.py mine --miner [ADDRESS] --url http://127.0.0.1:8001
python main.py send --wallet wallet.json --to [ADDRESS] --amount 10 --fee 0.1 --url http://127.0.0.1:8001
python main.py sync --url http://127.0.0.1:8001
python main.py validate --url http://127.0.0.1:8001

Тести
```bash
python -m unittest discover -s tests -v
python main.py experiment --runs 10 --difficulties 1,2,3,4 --output mining_experiment.png
```

API
- `GET /status`, `GET /chain`, `GET /mempool`, `GET /balance?address=...`
- `POST /transaction` — передати транзакцію
- `POST /mine` — намайнити блок (`{"miner":"address"}`)
- `POST /peers` — додати сусіда (`{"url":"http://..."}`)
- `POST /sync` — синхронізуватися з відомими вузлами
- `POST /block` — прийняти блок від сусіда
- `POST /chain/replace` — перевірити та прийняти альтернативний ланцюг
