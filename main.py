import os
import threading
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

API_KEY = os.environ.get("BITGET_API_KEY")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE")

bitget = ccxt.bitget({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'password': PASSPHRASE,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

def process_order(data):
    """비트겟 주문 실행 함수 (백그라운드 비동기)"""
    try:
        action = data.get('action')
        raw_symbol = data.get('symbol', 'SOXLUSDT')
        
        clean_symbol = raw_symbol.replace(".P", "").replace("/", "")
        if clean_symbol.endswith("USDT"):
            base = clean_symbol[:-4]
            symbol = f"{base}/USDT:USDT"
        else:
            symbol = clean_symbol

        bitget.load_markets()

        try:
            bitget.set_leverage(4, symbol)
        except Exception as lev_err:
            print(f"Leverage Notice: {str(lev_err)}")

        if action == 'buy':
            balance = bitget.fetch_balance()
            usdt_free = float(balance['USDT']['free'])
            
            ticker = bitget.fetch_ticker(symbol)
            current_price = float(ticker['last'])
            
            amount = (usdt_free * 4) / current_price
            
            stop_price = float(data.get('stop'))
            target_price = float(data.get('target'))

            params = {
                'stopLoss': {'triggerPrice': stop_price},
                'takeProfit': {'triggerPrice': target_price}
            }
            
            order = bitget.create_order(symbol, 'market', 'buy', amount, params=params)
            print(f"Order Executed Successfully: {order['id']}")

        elif action == 'close':
            positions = bitget.fetch_positions([symbol])
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0 and pos.get('side') == 'long':
                    bitget.create_order(symbol, 'market', 'sell', contracts, params={'reduceOnly': True})
            print("Long Position Closed Successfully")

    except Exception as e:
        print(f"Async Order Execution Error: {str(e)}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"status": "error", "message": "No JSON Data"}), 400

    # 백그라운드 쓰레드로 주문 비동기 실행 (트레이딩뷰 타임아웃 완벽 차단)
    threading.Thread(target=process_order, args=(data,)).start()

    # 트레이딩뷰에는 즉시 성공 200 반환 (0.05초 소요)
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
