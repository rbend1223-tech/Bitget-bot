import os
import threading
import requests
from flask import Flask, request, jsonify
import ccxt

app = Flask(__name__)

# Render 환경변수 로드
API_KEY = os.environ.get("BITGET_API_KEY")
SECRET_KEY = os.environ.get("BITGET_SECRET_KEY")
PASSPHRASE = os.environ.get("BITGET_PASSPHRASE")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 비트겟 API 설정
bitget = ccxt.bitget({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'password': PASSPHRASE,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

def send_telegram(message):
    """텔레그램 메시지 전송 함수"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token or Chat ID is missing")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram Send Error: {str(e)}")

def process_order(data):
    """비트겟 주문 실행 및 텔레그램 알림 처리"""
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
            
            # 텔레그램 매수 알림
            msg = (
                f"🚀 **[비트겟 매수 완료]**\n\n"
                f"• **종목**: {symbol}\n"
                f"• **진입가**: ${current_price:,.2f}\n"
                f"• **수량**: {amount:,.2f}\n"
                f"• **손절가(SL)**: ${stop_price:,.2f}\n"
                f"• **익절가(TP)**: ${target_price:,.2f}"
            )
            send_telegram(msg)

        elif action == 'close':
            positions = bitget.fetch_positions([symbol])
            closed = False
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0 and pos.get('side') == 'long':
                    bitget.create_order(symbol, 'market', 'sell', contracts, params={'reduceOnly': True})
                    closed = True
            
            if closed:
                # 텔레그램 청산 알림
                msg = f"🛑 **[비트겟 포지션 청산 완료]**\n\n• **종목**: {symbol}\n• **상태**: 롱 포지션 종료"
                send_telegram(msg)

    except Exception as e:
        error_msg = f"⚠️ **[비트겟 주문 오류 발생]**\n\n`{str(e)}`"
        send_telegram(error_msg)
        print(f"Async Order Execution Error: {str(e)}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"status": "error", "message": "No JSON Data"}), 400

    # 백그라운드 쓰레드로 주문 실행 + 텔레그램 전송
    threading.Thread(target=process_order, args=(data,)).start()

    # 트레이딩뷰에는 즉시 성공 200 반환 (타임아웃 방지)
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
