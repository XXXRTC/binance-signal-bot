import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

app = Flask(__name__)

# API keys από περιβάλλον (Render env vars ή τοπικά)
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

if not api_key or not api_secret:
    print("[ERROR] Binance API key or secret not set in environment variables!")

client = Client(api_key, api_secret)
client.FUTURES_URL = 'https://fapi.binance.com'

symbol = 'ETHUSDT'
safety_buffer = 0.98  # Χρησιμοποιούμε το 98% του διαθέσιμου κεφαλαίου

@app.route('/')
def index():
    return "🚀 Binance ETHUSDT Futures Signal Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("📥 Webhook received:", data)

        if not data:
            print("[ERROR] No JSON data received!")
            return jsonify({"error": "No JSON data"}), 400

        if data.get("symbol") != symbol:
            print(f"[ERROR] Wrong symbol: {data.get('symbol')}")
            return jsonify({"error": "Invalid symbol"}), 400

        action = data.get("signal")
        if action not in ["buy", "sell"]:
            print(f"[ERROR] Invalid signal: {action}")
            return jsonify({"error": "Invalid signal"}), 400

        # Παίρνουμε ισορροπία USDT futures wallet
        balances = client.futures_account_balance()
        usdt_balance = next((float(b['balance']) for b in balances if b['asset'] == 'USDT'), 0)
        print(f"[INFO] USDT Futures Balance: {usdt_balance}")

        if usdt_balance < 10:
            print("[ERROR] Insufficient balance")
            return jsonify({"error": "Insufficient balance"}), 400

        mark_price_data = client.futures_mark_price(symbol=symbol)
        mark_price = float(mark_price_data['markPrice'])
        print(f"[INFO] Mark price: {mark_price}")

        qty = round((usdt_balance * safety_buffer) / mark_price, 3)
        print(f"[INFO] Order quantity: {qty}")

        if qty < 0.001:
            print("[ERROR] Quantity too small to place an order")
            return jsonify({"error": "Quantity too small"}), 400

        positions = client.futures_position_information(symbol=symbol)
        pos_amt = float(positions[0]['positionAmt'])
        print(f"[INFO] Current position amount: {pos_amt}")

        # Κλείσιμο υπάρχουσας θέσης
        if pos_amt > 0 and action == "sell":
            print(f"[ACTION] Closing LONG position of {pos_amt}")
            client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=abs(pos_amt)
            )
        elif pos_amt < 0 and action == "buy":
            print(f"[ACTION] Closing SHORT position of {pos_amt}")
            client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=abs(pos_amt)
            )

        # Άνοιγμα νέας θέσης ανάλογα με το σήμα
        if action == "buy" and pos_amt <= 0:
            print(f"[ACTION] Opening LONG position {qty}")
            client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=qty
            )
            print(f"✅ Opened LONG {qty} {symbol}")

        elif action == "sell" and pos_amt >= 0:
            print(f"[ACTION] Opening SHORT position {qty}")
            client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=qty
            )
            print(f"🔻 Opened SHORT {qty} {symbol}")

        return jsonify({"status": "success"}), 200

    except BinanceAPIException as e:
        print(f"[BINANCE API ERROR] {e.status_code} - {e.message}")
        return jsonify({"error": "Binance API error", "message": str(e)}), 500

    except BinanceOrderException as e:
        print(f"[BINANCE ORDER ERROR] {e.status_code} - {e.message}")
        return jsonify({"error": "Binance order error", "message": str(e)}), 500

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return jsonify({"error": "Unexpected error", "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
