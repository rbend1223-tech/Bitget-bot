import os
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# Render 환경변수 로드
API_KEY = os.environ.get("BITGET_API_KEY")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE")

# 비트겟 API 설정 (유니파이드 계정 V2 대응)
bitget = ccxt.bitget({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'password': PASSPHRASE,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'
    }
})

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # 415 에러 방지: Content-Type에 상관없이 JSON 데이터 강제 추출
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Invalid JSON or Empty Data"}), 400

        action = data.get('action')
        raw_symbol = data.get('symbol', 'SOXLUSDT')
        
        # CCXT 비트겟 심볼 포맷 자동 변환 ('SOXLUSDT' -> 'SOXL/USDT:USDT')
        clean_symbol = raw_symbol.replace(".P", "").replace("/", "")
        if clean_symbol.endswith("USDT"):
            base = clean_symbol[:-4]
            symbol = f"{base}/USDT:USDT"
        else:
            symbol = clean_symbol

        # 마켓 정보 사전 로드
        bitget.load_markets()

        # 레버리지 설정 (유니파이드 계정 모드 예외 처리)
        try:
            bitget.set_leverage(4, symbol)
        except Exception as lev_err:
            print(f"Leverage Notice (Ignored): {str(lev_err)}")

        if action == 'buy':
            balance = bitget.fetch_balance()
            usdt_free = float(balance['USDT']['free'])
            
            ticker = bitget.fetch_ticker(symbol)
            current_price = float(ticker['last'])
            
            # (자유 잔고 * 4배) / 현재가 = 수량 계산
            amount = (usdt_free * 4) / current_price
            
            stop_price = float(data.get('stop'))
            target_price = float(data.get('target'))

            params = {
                'stopLoss': {'triggerPrice': stop_price},
                'takeProfit': {'triggerPrice': target_price}
            }
            
            order = bitget.create_order(symbol, 'market', 'buy', amount, params=params)
            return jsonify({"status": "success", "order_id": order['id']}), 200

        elif action == 'close':
            positions = bitget.fetch_positions([symbol])
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0 and pos.get('side') == 'long':
                    bitget.create_order(symbol, 'market', 'sell', contracts, params={'reduceOnly': True})
            return jsonify({"status": "success", "message": "Long Position Closed"}), 200

        return jsonify({"status": "ignored", "message": "Unknown Action"}), 200

    except Exception as e:
        print(f"Server Error Details: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
