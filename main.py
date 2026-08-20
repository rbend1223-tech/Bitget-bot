import os
import traceback
import ccxt
from flask import Flask, jsonify, request

app = Flask(__name__)

API_KEY = os.environ.get("BITGET_API_KEY", "")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY", "")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE", "")

exchange = ccxt.bitget(
    {
        "apiKey": API_KEY,
        "secret": SECRET_KEY,
        "password": PASSPHRASE,
        "options": {
            "defaultType": "swap",
        },
    }
)


@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200


@app.route("/webhook", methods=["POST", "GET", "HEAD"])
def webhook():
    if request.method in ["GET", "HEAD"]:
        return "Webhook Endpoint Ready", 200

    raw_text = request.get_data(as_text=True)
    print(f"📢 [RECEIVED PAYLOAD]: {raw_text}")

    try:
        data = request.get_json(force=True)

        action = str(data.get("action", "")).lower()
        symbol = data.get("symbol", "BTCUSDT")
        contracts = float(data.get("contracts", 0.01))

        if "/" not in symbol:
            symbol_formatted = f"{symbol.replace('USDT', '')}/USDT:USDT"
        else:
            symbol_formatted = symbol

        print(
            f"🚀 [비트겟 주문 시도] 방향: {action.upper()} | 종목: {symbol_formatted} | 수량: {contracts}"
        )

        # 비트겟 헷징모드 파라미터 분기
        if action in ["buy", "long"]:
            # 롱 진입
            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "holdSide": "long",
                "tradeSide": "open",
            }
            order = exchange.create_market_buy_order(
                symbol_formatted, contracts, params=params
            )

        elif action in ["sell", "short"]:
            # 숏 진입 또는 롱 청산
            # 트레이딩뷰 액션에 따라 선택: 기본은 숏 진입(open), 청산 신호면 close 처리
            is_close = data.get("close", False) # payload에 close: true가 있으면 청산 처리

            params = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT",
                "holdSide": "long" if is_close else "short",
                "tradeSide": "close" if is_close else "open",
            }
            order = exchange.create_market_sell_order(
                symbol_formatted, contracts, params=params
            )
        else:
            return (
                jsonify(
                    {"status": "error", "message": f"Invalid action: {action}"}
                ),
                400,
            )

        print(f"✅ [비트겟 주문 성공] Order ID: {order['id']}")
        return jsonify({"status": "success", "order_id": order["id"]}), 200

    except Exception as e:
        print(f"❌ [주문 실패 / 에러 발생]: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
