import os, time, threading, requests, base64, json, asyncio
import websockets
from flask import Flask
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
BUY_AMOUNT = 0.004
BUY_DELAY = 35  # زدنا الانتظار من 18 لـ 35 ثانية
SELL_DELAY = 70

app = Flask(__name__)
keypair = None
try:
    if PRIVATE_KEY:
        keypair = Keypair.from_base58_string(PRIVATE_KEY.strip())
        print(f"Wallet OK: {keypair.pubkey()}", flush=True)
except Exception as e:
    print(f"Wallet err: {e}", flush=True)

seen = set()

def send_tx(tx):
    try:
        b64 = base64.b64encode(bytes(tx)).decode()
        data = {"jsonrpc":"2.0","id":1,"method":"sendTransaction","params":[b64, {"encoding":"base64","skipPreflight":True}]}
        r = requests.post(RPC_URL, json=data, timeout=15)
        print(f"TX sent: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"send err: {e}", flush=True)

def trade(mint, sym):
    if not keypair: return
    try:
        print(f"Waiting {BUY_DELAY}s for {sym} {mint[:6]} to be indexed...", flush=True)
        time.sleep(BUY_DELAY)
        
        # نحاول 3 مرات لو قال 404
        for attempt in range(3):
            print(f"Buying {sym} attempt {attempt+1}...", flush=True)
            payload = {
                "publicKey": str(keypair.pubkey()),
                "action": "buy",
                "mint": mint,
                "denominatedInSol": "true",
                "amount": BUY_AMOUNT,
                "slippage": 30,
                "priorityFee": 0.002,
                "pool": "auto"
            }
            res = requests.post("https://pumpportal.fun/api/trade-local-validation", json=payload, timeout=30)
            print(f"Buy API {res.status_code}: {res.text[:250]}", flush=True)
            
            if res.status_code == 200:
                break
            if res.status_code == 404:
                print(f"Not indexed yet, retry in 7s...", flush=True)
                time.sleep(7)
                continue
            else:
                return

        if res.status_code != 200:
            print(f"Failed to buy {sym} after retries", flush=True)
            return

        b64tx = res.text.strip().strip('"')
        tx = VersionedTransaction.from_bytes(base64.b64decode(b64tx))
        tx.sign([keypair])
        send_tx(tx)
        print(f"BOUGHT {sym} {mint[:6]}", flush=True)
        
        time.sleep(SELL_DELAY)
        print(f"Selling {sym} 100%...", flush=True)
        payload2 = {"publicKey":str(keypair.pubkey()),"action":"sell","mint":mint,"denominatedInSol":"false","amount":"100%","slippage":30,"priorityFee":0.002,"pool":"auto"}
        res2 = requests.post("https://pumpportal.fun/api/trade-local-validation", json=payload2, timeout=30)
        print(f"Sell API {res2.status_code}", flush=True)
        b64tx2 = res2.text.strip().strip('"')
        tx2 = VersionedTransaction.from_bytes(base64.b64decode(b64tx2))
        tx2.sign([keypair])
        send_tx(tx2)
        print(f"SOLD {sym}", flush=True)
    except Exception as e:
        print(f"trade err {e}", flush=True)

async def ws_loop():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("WebSocket CONNECTED", flush=True)
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
                print("Subscribed - waiting for new coins...", flush=True)
                async for message in ws:
                    try:
                        data = json.loads(message)
                        mint = data.get("mint")
                        sym = data.get("symbol","?")
                        if mint and mint not in seen:
                            seen.add(mint)
                            print(f"NEW {sym} {mint[:6]} via WS", flush=True)
                            threading.Thread(target=trade, args=(mint,sym), daemon=True).start()
                    except:
                        pass
        except Exception as e:
            print(f"WS down {e} - retry 5s", flush=True)
            await asyncio.sleep(5)

def start_ws():
    asyncio.run(ws_loop())

threading.Thread(target=start_ws, daemon=True).start()

@app.route('/')
def home():
    return f"Bot Live WS V4 - Seen {len(seen)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
