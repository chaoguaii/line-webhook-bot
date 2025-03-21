from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/webhook", methods=["GET", "POST"])  # รับเฉพาะ POST
def webhook():
    data = request.get_json()
    return jsonify({"message": "Received", "data": data})
@app.route("/", methods=["GET"])
def home():
    return "Flask Server Running", 200


if __name__ == "__main__":
    app.run(port=8080)
