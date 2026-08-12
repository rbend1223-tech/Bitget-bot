import os
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# Render 환경변수에서 API 키 로드
API_KEY = os.environ.get("BITGET_API_KEY")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE")

# 비트겟 선물 API 객체 생성
bitget = ccxt.bitget({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'password': PASSPHRASE,
    'options': {'defaultType': 'swap'}
})

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No Data Received"}), 400

        action = data.get('action')
        symbol = data.get('symbol', 'SOXLUSDT')

        # 1. 레버리지 4배 설정
        bitget.set_leverage(4, symbol)

        if action == 'buy':
            # 계좌의 USDT 잔고 조회 및 주문 수량 산출
            balance = bitget.fetch_balance()
            usdt_free = float(balance['USDT']['free'])
            
            ticker = bitget.fetch_ticker(symbol)
            current_price = float(ticker['last'])
            
            # (자유 잔고 * 4배 레버리지) / 현재가 = 매수 수량
            amount = (usdt_free * 4) / current_price
            
            stop_price = float(data.get('stop'))
            target_price = float(data.get('target'))

            # TP/SL(익절가/손절가) 예약 옵션을 포함한 롱 시장가 진입
            params = {
                'stopLoss': {'triggerPrice': stop_price},
                'takeProfit': {'triggerPrice': target_price}
            }
            
            order = bitget.create_order(symbol, 'market', 'buy', amount, params=params)
            return jsonify({"status": "success", "order_id": order['id']}), 200

        elif action == 'close':
            # 현재 열려있는 롱 포지션 조회 후 시장가 청산
            positions = bitget.fetch_positions([symbol])
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0 and pos.get('side') == 'long':
                    bitget.create_order(symbol, 'market', 'sell', contracts, params={'reduceOnly': True})
            return jsonify({"status": "success", "message": "Long Position Closed"}), 200

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)