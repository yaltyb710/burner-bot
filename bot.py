import os
import time
import threading
from flask import Flask

# ===== راس مالك الحالي $6.03 - خطة آمنة بدون ايقاف =====
BUY_AMOUNT_SOL = float(os.getenv("BUY_AMOUNT", "0.004"))  # قللت ليك لـ 0.004 ~ $0.41 عشان تحافظ على الـ $6
BUY_DELAY_SEC = int(os.getenv("BUY_DELAY", "18"))
SELL_DELAY_SEC = int(os.getenv("SELL_DELAY", "70"))

print(f"🔥 Burner Bot $6.03 Mode | Buy: {BUY_AMOUNT_SOL} SOL | Buy after: {BUY_DELAY_SEC}s | Sell after: {SELL_DELAY_SEC}s | No Stop Limit")

# سيرفر وهمي عشان Render المجاني
app = Flask(__name__)

@app.route("/")
def home():
    return f"Burner Bot Live $6.03 | {BUY_AMOUNT_SOL} SOL | Free Mode | No Limit"

@app.route("/health")
def health():
    return "OK", 200

def burner_logic():
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Scanning pump.fun... buy in {BUY_DELAY_SEC}s with {BUY_AMOUNT_SOL} SOL")
            time.sleep(BUY_DELAY_SEC)
            
            # هنا كود الشراء الحقيقي بتاعك
            # buy_token(amount=BUY_AMOUNT_SOL)
            print(f"✅ BUY {BUY_AMOUNT_SOL} SOL executed")
            
            print(f"⏳ Holding {SELL_DELAY_SEC}s...")
            time.sleep(SELL_DELAY_SEC)
            
            # هنا كود البيع
            # sell_token()
            print(f"💰 SELL executed - Let it run freely")
            
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

threading.Thread(target=burner_logic, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
