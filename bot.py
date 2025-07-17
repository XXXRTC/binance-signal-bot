import os
from flask import Flask, request, jsonify
from binance.client import Client

app = Flask(__name__)

# API keys από περιβάλλον ή Render env vars
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

client = Client(api_key, api_secret)
client.FUTURES_URL = 'https://fapi.binance.com'

symbol = 'ETHUSDT'
safety_buffer = 0.98  # Χρησιμοποιούμε το 98% του διαθέσιμου κεφαλαίου

@app.route('/')
def index():
    return "🚀 Binance ETHUSDT Futures Signal Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📥 Webhook received:", data)

    if data.get("symbol") == symbol:
        action = data.get("signal")
        if action not in ["buy", "sell"]:
            return jsonify({"error": "Invalid signal"}), 400

        # Παίρνουμε ισορροπία USDT futures wallet
        balances = client.futures_account_balance()
        usdt_balance = next((float(b['balance']) for b in balances if b['asset'] == 'USDT'), 0)

        if usdt_balance < 10:
            return jsonify({"error": "Insufficient balance"}), 400

        # Τιμή mark price
        mark_price_data = client.futures_mark_price(symbol=symbol)
        mark_price = float(mark_price_data['markPrice'])

        # Υπολογίζουμε ποσότητα (98% του κεφαλαίου / τιμή)
        qty = round((usdt_balance * safety_buffer) / mark_price, 3)

        # Κλείσιμο υπάρχουσας θέσης
        positions = client.futures_position_information(symbol=symbol)
        pos_amt = float(positions[0]['positionAmt'])

        if pos_amt > 0:
            client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=abs(pos_amt)
            )
        elif pos_amt < 0:
            client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=abs(pos_amt)
            )

        # Άνοιγμα νέας θέσης ανάλογα με το σήμα
        if action == "buy":
            client.futures_create_order(
                symbol=symbol,
                side='BUY',
                type='MARKET',
                quantity=qty
            )
            print(f"✅ Opened LONG {qty} {symbol}")
        elif action == "sell":
            client.futures_create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=qty
            )
            print(f"🔻 Opened SHORT {qty} {symbol}")

        return jsonify({"status": "success"}), 200

    return jsonify({"error": "Invalid symbol"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
