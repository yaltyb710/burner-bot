import os, time, threading, requests, base64
from flask import Flask
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
BUY_AMOUNT = 0.004
BUY_DELAY = 18
SELL_DELAY = 70

app = Flask(__name__)

keypair = None
try:
    if PRIVATE_KEY:
        keypair = Keypair.from_base58_string(PRIVATE_KEY.strip())
        print(f"Wallet loaded: {keypair.pubkey()}")
except Exception as e:
    print(f"Wallet error: {e}")

seen = set()

def send_tx(tx):
    try:
        b64 = base64.b64encode(bytes(tx)).decode('utf-8')
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [b64, {"encoding": "base64", "skipPreflight": True}]
        }
        r = requests.post(RPC_URL, json=data, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def get_coins():
    try:
        r = requests.get("https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created_timestamp&order=DESC&includeNsfw=false", timeout=10)
        return r.json()
    except:
        return []

def trade(mint):
    if not keypair:
        return
    try:
        print(f"Waiting {BUY_DELAY}s for {mint[:6]}")
        time.sleep(BUY_DELAY)
        print(f"Buying {mint[:6]} {BUY_AMOUNT} SOL")
        payload = {
            "publicKey": str(keypair.pubkey()),
            "action": "buy",
            "mint": mint,
            "denominatedInSol": "true",
            "amount": BUY_AMOUNT,
            "slippage": 15,
            "priorityFee": 0.0001,
            "pool": "pump"
        }
        res = requests.post("https://pumpportal.fun/api/trade-local-validation", json=payload, timeout=30)
        if res.status_code != 200:
            print(f"Buy fail: {res.text[:200]}")
            return
        b64tx = res.text.strip().strip('"').strip("'")
        tx_bytes = base64.b64decode(b64tx)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        tx.sign([keypair])
        result = send_tx(tx)
        print(f"BOUGHT {mint[:6]} {result}")

        time.sleep(SELL_DELAY)
        print(f"Selling {mint[:6]}")
        payload2 = {
            "publicKey": str(keypair.pubkey()),
            "action": "sell",
            "mint": mint,
            "denominatedInSol": "false",
            "amount": "100%",
            "slippage": 15,
            "priorityFee": 0.0001,
            "pool": "pump"
        }
        res2 = requests.post("https://pumpportal.fun/api/trade-local-validation", json=payload2, timeout=30)
        b64tx2 = res2.text.strip().strip('"').strip("'")
        tx_bytes2 = base64.b64decode(b64tx2)
        tx2 = VersionedTransaction.from_bytes(tx_bytes2)
        tx2.sign([keypair])
        result2 = send_tx(tx2)
        print(f"SOLD {mint[:6]} {result2}")
    except Exception as e:
        print(f"Trade err {mint[:6]}: {e}")

def loop():
    while True:
        try:
            for c in get_coins():
                m = c.get('mint')
                if m and m not in seen:
                    seen.add(m)
                    print(f"NEW {c.get('symbol')} {m[:6]}")
                    threading.Thread(target=trade, args=(m,), daemon=True).start()
        except Exception as e:
            print(f"loop err {e}")
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def home():
    return f"Bot Live {keypair.pubkey() if keypair else 'no key'}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
