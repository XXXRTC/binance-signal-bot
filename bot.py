from flask import Flask, request, jsonify
import os
import requests
import hmac
import hashlib
import time

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

BASE_URL = "https://fapi.binance.com"

def send_order(symbol, side):
    timestamp = int(time.time() * 1000)
    params = f"symbol={symbol}&side={side.upper()}&type=MARKET&quantity=100&timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}/fapi/v1/order?{params}&signature={signature}"
    headers = {"X-MBX-APIKEY": API_KEY}
    res = requests.post(url, headers=headers)
    return res.json()

@app.route("/", methods=["POST"])
def handle_alert():
    data = request.json
    symbol = data.get("symbol")
    action = data.get("action")

    if not symbol or not action:
        return jsonify({"error": "Missing symbol or action"}), 400

    try:
        response = send_order(symbol, action)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "Binance Signal Bot is running."
