import os
import traceback
import ccxt
from flask import Flask, jsonify, request

app = Flask(__name__)

# Render Environment Variables(환경변수)에서 비트겟 API 키를 불러옵니다.
API_KEY = os.environ.get("BITGET_API_KEY", "")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY", "")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE", "")

# ccxt 비트겟 선물 거래 객체 생성
exchange = ccxt.bitget(
    {
        "apiKey": API_KEY,
        "secret": SECRET_KEY,
        "password": PASSPHRASE,
        "options": {
            "defaultType": "swap",  # 선물 거래(USDT-M) 설정
        },
    }
)


# 1. UptimeRobot용 Health Check (서버 다운 방지)
@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200


# 2. 트레이딩뷰 웹훅 수신 및 비트겟 실제 주문 실행
@app.route("/webhook", methods=["POST", "GET", "HEAD"])
def webhook():
    if request.method in ["GET", "HEAD"]:
        return "Webhook Endpoint Ready", 200

    raw_text = request.get_data(as_text=True)
    print(f"📢 [RECEIVED PAYLOAD]: {raw_text}")

    try:
        data = request.get_json(force=True)

        action = str(data.get("action", "")).lower()  # "buy" 또는 "sell"
        symbol = data.get("symbol", "SOXLUSDT")  # 예: "SOXLUSDT"
        contracts = float(data.get("contracts", 1))  # 수량

        # 심볼 포맷 변환 (SOXLUSDT -> SOXL/USDT:USDT)
        if "/" not in symbol:
            symbol_formatted = f"{symbol.replace('USDT', '')}/USDT:USDT"
        else:
            symbol_formatted = symbol

        print(
            f"🚀 [비트겟 주문 시도] 방향: {action.upper()} | 종목: {symbol_formatted} | 수량: {contracts}"
        )

        # 비트겟 시장가 주문 실행
        if action in ["buy", "long"]:
            order = exchange.create_market_buy_order(
                symbol_formatted, contracts
            )
        elif action in ["sell", "short"]:
            order = exchange.create_market_sell_order(
                symbol_formatted, contracts
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid action: {action}",
                    }
                ),
                400,
            )

        print(f"✅ [비트겟 주문 성공] Order ID: {order['id']}")
        return (
            jsonify(
                {
                    "status": "success",
                    "order_id": order["id"],
                    "details": order,
                }
            ),
            200,
        )

    except Exception as e:
        print(f"❌ [주문 실패 / 에러 발생]: {str(e)}")
        traceback.print_exc()
        return (
            jsonify(
                {"status": "error", "message": str(e), "raw_payload": raw_text}
            ),
            400,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
