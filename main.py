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

        # 1. 헷징 모드 옵션
        hedge_params = {
            "productType": "USDT-FUTURES",
            "posMode": "hedge_mode",
            "tradeSide": "open",
            "holdSide": "long" if action in ["buy", "long"] else "short",
        }

        # 2. 단방향 모드 옵션
        oneway_params = {"productType": "USDT-FUTURES"}

        order = None
        try:
            # 우선 헷징 모드로 시도
            if action in ["buy", "long"]:
                order = exchange.create_market_buy_order(
                    symbol_formatted, contracts, params=hedge_params
                )
            elif action in ["sell", "short"]:
                order = exchange.create_market_sell_order(
                    symbol_formatted, contracts, params=hedge_params
                )
        except Exception as err:
            # 25156 에러 발생 시 단방향 파라미터로 즉시 재시도
            if "25156" in str(err) or "one-way" in str(err).lower():
                print("⚠️ [단방향 규격 요구 감지] 단방향 파라미터로 즉시 재시도합니다.")
                if action in ["buy", "long"]:
                    order = exchange.create_market_buy_order(
                        symbol_formatted, contracts, params=oneway_params
                    )
                elif action in ["sell", "short"]:
                    order = exchange.create_market_sell_order(
                        symbol_formatted, contracts, params=oneway_params
                    )
            else:
                raise err

        print(f"✅ [비트겟 주문 성공] Order ID: {order['id']}")
        return jsonify({"status": "success", "order_id": order["id"]}), 200

    except Exception as e:
        print(f"❌ [주문 실패 / 에러 발생]: {str(e)}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
