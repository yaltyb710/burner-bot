import os, time, threading, requests, base64
from flask import Flask
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
BUY_AMOUNT = 0.004
BUY_DELAY = 18
SELL_DELAY = 70

app = Flask(__name__)

# تحميل المحفظة
keypair = None
client = None
try:
    if PRIVATE_KEY:
        keypair = Keypair.from_base58_string(PRIVATE_KEY.strip())
        client = Client(RPC_URL)
        print(f"Wallet: {keypair.pubkey()}")
    else:
        print("No PRIVATE_KEY found")
except Exception as e:
    print(f"Wallet error: {e}")

seen = set()

def get_coins():
    try:
        r = requests.get("https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created_timestamp&order=DESC&includeNsfw=false", timeout=10)
        return r.json()
    except:
        return []

def trade(mint):
    if not keypair or not client:
        print("No wallet, skip trade")
        return
    try:
        print(f"Waiting {BUY_DELAY}s for {mint[:6]}...")
        time.sleep(BUY_DELAY)
        print(f"Buying {mint[:6]} with {BUY_AMOUNT} SOL")
        
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
            print(f"Buy API failed: {res.text[:200]}")
            return
        tx_b64 = res.json() if isinstance(res.json(), str) else res.text.strip()
        # clean quotes
        tx_b64 = tx_b64.strip().strip('"')
        tx_bytes = base64.b64decode(tx_b64)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        tx.sign([keypair])
        sig = client.send_transaction(tx).value
        print(f"BOUGHT {mint[:6]} https://solscan.io/tx/{sig}")

        time.sleep(SELL_DELAY)
        print(f"Selling {mint[:6]} 100%")
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
        if res2.status_code != 200:
            print(f"Sell API failed: {res2.text[:200]}")
            return
        tx_b64_2 = (res2.json() if isinstance(res2.json(), str) else res2.text).strip().strip('"')
        tx_bytes2 = base64.b64decode(tx_b64_2)
        tx2 = VersionedTransaction.from_bytes(tx_bytes2)
        tx2.sign([keypair])
        sig2 = client.send_transaction(tx2).value
        print(f"SOLD {mint[:6]} https://solscan.io/tx/{sig2}")

    except Exception as e:
        print(f"Trade failed {mint[:6]}: {e}")

def loop():
    while True:
        try:
            coins = get_coins()
            for c in coins:
                m = c.get('mint')
                if m and m not in seen:
                    seen.add(m)
                    print(f"NEW {c.get('symbol')} {m[:6]} MC ${c.get('usd_market_cap',0):.0f}")
                    threading.Thread(target=trade, args=(m,), daemon=True).start()
        except Exception as e:
            print(f"Loop err {e}")
        print(f"Scanning... buy {BUY_AMOUNT} after {BUY_DELAY}s")
        time.sleep(5)

threading.Thread(target=loop, daemon=True).start()

@app.route('/')
def home():
    return f"Bot Live - {keypair.pubkey() if keypair else 'No wallet'}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
