import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import update_labels
import time

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": os.environ.get("CORS_ORIGINS", "*")}})

SECRET = os.environ.get("UPDATE_SECRET", "supersecret")
LAST_RUN_FILE = "/tmp/last_run.txt"
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", "86400"))

def read_last_run():
  try:
    if os.path.exists(LAST_RUN_FILE):
      with open(LAST_RUN_FILE, "r") as f:
        return float(f.read().strip())
  except Exception:
    return None
  return None

@app.route("/")
def home():
  return "Label updater is alive."

@app.route("/api/status", methods=["GET"])
def status():
  ts = read_last_run()
  iso = None
  if ts:
    try:
      iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
    except Exception:
      iso = None
  return jsonify({
    "last_run": iso,
    "cooldown_seconds": COOLDOWN_SECONDS
  })

@app.route("/api/run", methods=["POST"])
def api_run():
  auth = request.headers.get("Authorization", "")
  if not auth.startswith("Bearer ") or auth.split("Bearer ")[1] != SECRET:
    abort(403)
  summary = update_labels.main()  # updates LAST_RUN_FILE internally
  return jsonify({"status": "ok", "summary": summary})

if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
