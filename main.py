import traceback
from flask import Flask, jsonify, request

app = Flask(__name__)


# 1. UptimeRobot용 메인 핑 수신 (HEAD/GET 허용)
@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200


# 2. 트레이딩뷰 웹훅 수신 라우터
@app.route("/webhook", methods=["POST", "GET", "HEAD"])
def webhook():
    # UptimeRobot이 /webhook으로 핑을 쏠 경우 대응
    if request.method in ["GET", "HEAD"]:
        return "Webhook Endpoint Ready", 200

    # 트레이딩뷰에서 들어온 데이터 원본 로그 출력
    raw_text = request.get_data(as_text=True)
    print(f"📢 [RECEIVED PAYLOAD]: {raw_text}")

    try:
        data = request.get_json(force=True)

        # ----------------------------------------------------
        # TODO: 비트겟 주문 로직 (기존에 작성해두신 코드)
        # 예: symbol = data.get("symbol"), action = data.get("action")
        # ----------------------------------------------------

        return jsonify({"status": "success", "message": "Order executed"}), 200

    except Exception as e:
        print(f"❌ JSON 파싱 실패: {str(e)}")
        traceback.print_exc()
        return (
            jsonify({"status": "error", "message": "Invalid JSON format"}),
            400,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
