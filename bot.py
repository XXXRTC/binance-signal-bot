import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.exceptions import BinanceAPIException

app = Flask(__name__)

# API Keys από περιβάλλον
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
client = Client(api_key, api_secret)

# Config
symbol = 'ETHUSDC'
min_qty = 0.001  # Ελάχιστη ποσότητα

@app.route('/')
def index():
    return "🚀 Binance ETHUSDC Futures Signal Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📥 Webhook received:", data)

    if not data:
        return jsonify({"error": "Empty payload"}), 400

    if data.get("symbol") != symbol:
        return jsonify({"error": f"Symbol mismatch: expected {symbol}"}), 400

    signal = data.get("signal")
    if signal not in ["buy", "sell"]:
        return jsonify({"error": "Invalid signal"}), 400

    try:
        # ✅ Παίρνουμε διαθέσιμο USDC balance
        balances = client.futures_account_balance()
        usdc_balance = next((float(b['balance']) for b in balances if b['asset'] == 'USDC'), 0)
        print(f"💰 USDC Balance: {usdc_balance}")

        if usdc_balance < 10:
            return jsonify({"error": "Low balance (< $10)"}), 400

        # ✅ Παίρνουμε τρέχον mark price
        mark_price_data = client.futures_mark_price(symbol=symbol)
        mark_price = float(mark_price_data['markPrice'])
        print(f"📈 Mark Price: {mark_price}")

        # ✅ Παίρνουμε το τρέχον leverage
        pos_info = client.futures_position_information(symbol=symbol)
        leverage = int(pos_info[0]['leverage'])
        print(f"🔧 Current Leverage: x{leverage}")

        # ✅ Υπολογισμός ποσότητας (100% κεφαλαίου * leverage)
        notional = usdc_balance * leverage
        qty = round(notional / mark_price, 3)
        if qty < min_qty:
            return jsonify({"error": f"Quantity too small: {qty}"}), 400
        print(f"🧮 Calculated Quantity: {qty}")

        # ✅ Κλείνουμε προηγούμενη θέση (αν υπάρχει)
        pos_amt = float(pos_info[0]['positionAmt'])
        if pos_amt != 0:
            side = 'SELL' if pos_amt > 0 else 'BUY'
            close_qty = abs(pos_amt)
            print(f"⚠️ Closing previous position {side} {close_qty}")
            close_order = client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=close_qty
            )
            print(f"❌ Closed existing position: {close_order}")

        # ✅ Ανοίγουμε νέα θέση
        order_side = 'BUY' if signal == 'buy' else 'SELL'
        order = client.futures_create_order(
            symbol=symbol,
            side=order_side,
            type='MARKET',
            quantity=qty
        )
        print(f"✅ New {order_side} order placed: {order}")

        return jsonify({
            "status": "order placed",
            "signal": signal,
            "qty": qty,
            "leverage": leverage
        }), 200

    except BinanceAPIException as e:
        print(f"❌ Binance API Error: {e.message}")
        return jsonify({"error": e.message}), 500
    except Exception as ex:
        print(f"❌ Unexpected Error: {ex}")
        return jsonify({"error": str(ex)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
