import os, time, threading, requests, json, asyncio
import websockets
from flask import Flask
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction

PRIVATE_KEY = os.getenv("PRIVATE_KEY")
RPC_URL = os.getenv("RPC_URL")
BUY_AMOUNT = 0.004
BUY_DELAY = 35
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

def send_tx(signed_tx):
    try:
        import base64
        b64 = base64.b64encode(bytes(signed_tx)).decode()
        data = {"jsonrpc":"2.0","id":1,"method":"sendTransaction","params":[b64, {"encoding":"base64","skipPreflight":True}]}
        r = requests.post(RPC_URL, json=data, timeout=15)
        print(f"TX sent: {r.text[:300]}", flush=True)
    except Exception as e:
        print(f"send err: {e}", flush=True)

def trade(mint, sym):
    if not keypair: return
    try:
        print(f"Waiting {BUY_DELAY}s for {sym}...", flush=True)
        time.sleep(BUY_DELAY)
        payload = {"publicKey":str(keypair.pubkey()),"action":"buy","mint":mint,"denominatedInSol":"true","amount":BUY_AMOUNT,"slippage":30,"priorityFee":0.002,"pool":"auto"}
        res = requests.post("https://pumpportal.fun/api/trade-local", json=payload, timeout=30)
        print(f"Buy API {res.status_code} len {len(res.content)}", flush=True)
        if res.status_code != 200:
            print(f"Buy failed: {res.text[:200]}", flush=True)
            return
        tx = VersionedTransaction.from_bytes(res.content)
        # الطريقة الجديدة للتوقيع
        signed_tx = VersionedTransaction(tx.message, [keypair])
        send_tx(signed_tx)
        print(f"BOUGHT {sym} {mint[:6]} ✅", flush=True)
        time.sleep(SELL_DELAY)
        payload2 = {"publicKey":str(keypair.pubkey()),"action":"sell","mint":mint,"denominatedInSol":"false","amount":"100%","slippage":30,"priorityFee":0.002,"pool":"auto"}
        res2 = requests.post("https://pumpportal.fun/api/trade-local", json=payload2, timeout=30)
        if res2.status_code == 200:
            tx2 = VersionedTransaction.from_bytes(res2.content)
            signed_tx2 = VersionedTransaction(tx2.message, [keypair])
            send_tx(signed_tx2)
            print(f"SOLD {sym} ✅", flush=True)
    except Exception as e:
        print(f"trade err {e}", flush=True)

async def ws_loop():
    uri = "wss://pumpportal.fun/api/data"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("WebSocket CONNECTED", flush=True)
                await ws.send(json.dumps({"method": "subscribeNewToken"}))
                async for message in ws:
                    try:
                        data = json.loads(message)
                        mint = data.get("mint")
                        sym = data.get("symbol","?")
                        if mint and mint not in seen:
                            seen.add(mint)
                            print(f"NEW {sym} {mint[:6]}", flush=True)
                            threading.Thread(target=trade, args=(mint,sym), daemon=True).start()
                    except:
                        pass
        except Exception as e:
            print(f"WS down {e}", flush=True)
            await asyncio.sleep(5)

def start_ws():
    asyncio.run(ws_loop())

threading.Thread(target=start_ws, daemon=True).start()

@app.route('/')
def home():
    return f"Bot V7 FINAL WORKING - Seen {len(seen)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
