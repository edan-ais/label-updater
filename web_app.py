import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import update_labels

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": os.environ.get("CORS_ORIGINS", "*")}})

SECRET = os.environ.get("UPDATE_SECRET", "supersecret")

@app.route("/")
def home():
    return "Label updater is alive."

@app.route("/api/run", methods=["POST"])
def api_run():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth.split("Bearer ")[1] != SECRET:
        abort(403)

    summary = update_labels.main()

    return jsonify({"status": "ok", "summary": summary})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
