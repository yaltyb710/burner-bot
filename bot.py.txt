import asyncio, websockets, json, os, requests, time
from solders.keypair import Keypair
import base58

# --- إعدادات محفظتك الـ 6$ ---
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
BUY_AMOUNT_SOL = 0.009  # = 1$ تقريباً
SELL_DELAY = 70  # ثانية
BUY_DELAY = 18   # ثانية
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")

keypair = Keypair.from_bytes(base58.b58decode(PRIVATE_KEY))
WALLET = str(keypair.pubkey())
print(f"✅ بوت الـ 6$ شغال | المحفظة: {WALLET[:6]}... | كل صفقة: {BUY_AMOUNT_SOL} SOL")

def is_honeypot(mint):
    """فحص سريع هل العملة هوني بوت؟"""
    try:
        # 1. فحص rugcheck
        r = requests.get(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report", timeout=4)
        data = r.json()
        # لو السكور أقل من 300 أو فيه خطر كبير = سكام
        if data.get('score', 1000) < 300:
            print(f"⛔ Skip هوني بوت (score {data.get('score')}): {mint[:6]}")
            return True
        risks = [x['name'] for x in data.get('risks', [])]
        if 'High holder correlation' in str(risks) or 'Mutable' in str(risks):
            # ممكن نتجاوز ده لكن للـ 6$ نخليهو آمن
            pass
        return False
    except:
        # لو ما قدر يفحص، نعتبرها آمنة مؤقتاً
        return False

async def buy_and_sell_after(mint):
    try:
        print(f"⏳ انتظر {BUY_DELAY}ث لعملة {mint[:6]}...")
        await asyncio.sleep(BUY_DELAY)
        
        if is_honeypot(mint):
            return

        # --- شراء ---
        print(f"🚀 شراء {mint[:6]} بـ {BUY_AMOUNT_SOL} SOL")
        buy_payload = {
            "publicKey": WALLET,
            "action": "buy",
            "mint": mint,
            "amount": BUY_AMOUNT_SOL,
            "denominatedInSol": "true",
            "slippage": 20,
            "priorityFee": 0.0001, # قليل عشان رأس مالك صغير
            "pool": "pump"
        }
        res = requests.post("https://pumpportal.fun/api/trade-local", json=buy_payload, timeout=10)
        print(f"Buy: {res.status_code} - {res.text[:150]}")

        # --- انتظار 70 ثانية وبيع ---
        print(f"⏰ حأبيع {mint[:6]} بعد {SELL_DELAY} ثانية")
        await asyncio.sleep(SELL_DELAY)
        
        print(f"💰 بيع {mint[:6]}")
        sell_payload = {
            "publicKey": WALLET,
            "action": "sell",
            "mint": mint,
            "amount": "100%", # بيع كل الكمية
            "denominatedInSol": "false",
            "slippage": 20,
            "priorityFee": 0.0001,
            "pool": "pump"
        }
        res2 = requests.post("https://pumpportal.fun/api/trade-local", json=sell_payload, timeout=10)
        print(f"Sell: {res2.status_code} - {res2.text[:150]}")

    except Exception as e:
        print(f"Error trade {mint[:6]}: {e}")

async def main():
    uri = "wss://pumpportal.fun/api/data"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        print("👀 يراقب عملات pump الجديدة... (18ث دخول / 70ث خروج)")
        async for msg in ws:
            try:
                data = json.loads(msg)
                if 'mint' in data:
                    mint = data['mint']
                    # شغل كل صفقة في الخلفية عشان ما يعلق
                    asyncio.create_task(buy_and_sell_after(mint))
            except:
                continue

if __name__ == "__main__":
    asyncio.run(main())
