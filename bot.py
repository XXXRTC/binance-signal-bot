import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.exceptions import BinanceAPIException

app = Flask(__name__)

# API Keys από περιβάλλον (Render ή .env)
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

# Binance client
client = Client(api_key, api_secret)
client.FUTURES_URL = 'https://fapi.binance.com'

symbol = 'ETHUSDC'  # Αλλάξαμε σε ETHUSDC perp
safety_buffer = 0.98  # Χρησιμοποιούμε το 98% του κεφαλαίου για trade

@app.route('/')
def index():
    return "🚀 Binance ETHUSDC Futures Signal Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📥 Webhook Received:", data)

    if not data:
        return jsonify({"error": "Empty payload"}), 400

    if data.get("symbol") != symbol:
        return jsonify({"error": "Symbol mismatch"}), 400

    signal = data.get("signal")
    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    try:
        # Λήψη διαθέσιμου USDC balance
        balances = client.futures_account_balance()
        usdc_balance = next((float(b['balance']) for b in balances if b['asset'] == 'USDC'), 0)

        if usdc_balance < 10:
            return jsonify({"error": "Low balance"}), 400

        # Τιμή αγοράς (mark price)
        mark_price_data = client.futures_mark_price(symbol=symbol)
        mark_price = float(mark_price_data['markPrice'])
        qty = round((usdc_balance * safety_buffer) / mark_price, 3)

        if qty < 0.001:
            return jsonify({"error": "Quantity too small"}), 400

        # Κλείσιμο υπάρχουσας θέσης αν υπάρχει
        positions = client.futures_position_information(symbol=symbol)
        for pos in positions:
            pos_amt = float(pos['positionAmt'])
            if pos_amt != 0:
                side = 'SELL' if pos_amt > 0 else 'BUY'
                close_qty = abs(pos_amt)
                close_order = client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=close_qty
                )
                print(f"❌ Closed existing position: {close_order}")

        # Άνοιγμα νέας θέσης
        order_side = 'BUY' if signal == 'buy' else 'SELL'
        order = client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type='MARKET',
            quantity=qty
        )
        print(f"✅ Opened {signal.upper()} position: {order}")

        return jsonify({"status": "order placed", "signal": signal, "qty": qty}), 200

    except BinanceAPIException as e:
        print(f"❌ Binance API error: {e.message}")
        return jsonify({"error": e.message}), 500
    except Exception as ex:
        print(f"❌ Unexpected error: {ex}")
        return jsonify({"error": str(ex)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
