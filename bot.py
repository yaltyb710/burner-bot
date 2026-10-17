import os, time, threading, requests, base58, json
from flask import Flask
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction

# --- الاعدادات من Render ---
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
BUY_AMOUNT = 0.004
BUY_DELAY = 18
SELL_DELAY = 70

app = Flask(__name__)

# --- المحفظة ---
try:
    keypair = Keypair.from_base58_string(PRIVATE_KEY)
    client = Client(RPC_URL)
    print(f"🔥 Wallet loaded: {keypair.pubkey()}")
    print(f"🔥 Burner Bot $6.03 Mode | Buy: {BUY_AMOUNT} SOL | Buy after: {BUY_DELAY}s | Sell after: {SELL_DELAY}s")
except Exception as e:
    print(f"❌ Wallet Error: {e}")
    keypair = None

seen_mints = set()

def get_new_coins():
    try:
        url = "https://frontend-api.pump.fun/coins?offset=0&limit=10&sort=created_timestamp&order=DESC&includeNsfw=false"
        r = requests.get(url, timeout=10)
        return r.json()
    except:
        return []

def buy_and_sell(mint):
    try:
        print(f"⏳ Waiting {BUY_DELAY}s to buy {mint[:6]}...")
        time.sleep(BUY_DELAY)
        
        # --- شراء عبر pumpportal ---
        print(f"💸 Buying {mint[:6]} with {BUY_AMOUNT} SOL...")
        buy_payload = {
            "publicKey": str(keypair.pubkey()),
            "action": "buy",
            "mint": mint,
            "denominatedInSol": "true",
            "amount": BUY_AMOUNT,
            "slippage": 15,
            "priorityFee": 0.0001,
            "pool": "pump"
        }
        resp = requests.post("https://pumpportal.fun/api/trade-local-validation", json=buy_payload, timeout=20)
        tx_bytes = base58.b58decode(resp.json()) if isinstance(resp.json(), str) else base58.b58decode(resp.text.strip().strip('"'))
        # الطريقة الجديدة: pumpportal برجع base64
        import base64
        try:
            tx_data = base64.b64decode(resp.json())
        except:
            tx_data = base64.b64decode(resp.text)

        tx = VersionedTransaction.from_bytes(tx_data)
        tx.sign([keypair])
        sig = client.send_transaction(tx).value
        print(f"✅ BOUGHT! https://solscan.io/tx/{sig}")

        print(f"⏳ Waiting {SELL_DELAY}s to sell...")
        time.sleep(SELL_DELAY)

        # --- بيع 100% ---
        print(f"💰 Selling {mint[:6]}...")
        sell_payload = {
            "publicKey": str(keypair.pubkey()),
            "action": "sell",
            "mint": mint,
            "denominatedInSol": "false",
            "amount": "100%",
            "slippage": 15,
            "priorityFee": 0.0001,
            "pool": "pump"
        }
        resp2 = requests.post("https://pumpportal.fun/api/trade-local-validation", json=sell_payload, timeout=20)
        tx_data2 = base64.b64decode(resp2.json() if isinstance(resp2.json(), str) else resp2.text.strip().strip('"'))
        tx2 = VersionedTransaction.from_bytes(tx_data2)
        tx2.sign([keypair])
        sig2 = client.send_transaction(tx2).value
        print(f"✅ SOLD! https://solscan.io/tx/{sig2}")

    except Exception as e:
        print(f"❌ Trade failed {mint[:6]}: {e}")

def scanner_loop():
    while True:
        try:
            coins = get_new_coins()
            for coin in coins:
                mint = coin.get('mint')
                if mint and mint not in seen_mints:
                    seen_mints.add(mint)
                    print(f"🆕 New coin: {coin.get('symbol')} {mint[:6]} | MarketCap: ${coin.get('usd_market_cap',0):.2f}")
                    # شغل الشراء في ثريد منفصل
                    threading.Thread(target=buy_and_sell, args=(mint,), daemon=True).start()
            print(f"[{time.strftime('%H:%M:%S')}] Scanning pump.fun... buy in {BUY_DELAY}s with {BUY_AMOUNT} SOL")
        except Exception as e:
            print(f"Scan error: {e}")
        time.sleep(5)

threading.Thread(target=scanner_loop, daemon=True).start()

@app.route('/')
def home():
    return f"Burner Bot Live - Wallet: {keypair.pubkey() if keypair else 'No key'} - Scanning..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
