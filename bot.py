import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return "🚀 Binance ETHUSDT Signal Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("📥 Webhook received:", data)

    # Εδώ βάλε τη λογική σου για signals (π.χ. έλεγξε αν είναι buy/sell κλπ.)
    # Παράδειγμα:
    if data.get("symbol") == "ETHUSDT":
        signal = data.get("signal")
        if signal == "buy":
            print("✅ Buy signal received for ETHUSDT!")
        elif signal == "sell":
            print("🔻 Sell signal received for ETHUSDT!")

    return jsonify({"status": "success"}), 200

# Αυτό ΚΡΑΤΑ το app ζωντανό (Render requirement)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
