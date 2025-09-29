import os
from flask import Flask, request, abort
import update_labels

app = Flask(__name__)

SECRET = os.environ.get("UPDATE_SECRET", "supersecret")

@app.route("/")
def home():
    return "Label updater is alive."

@app.route("/run", methods=["GET"])
def run():
    if request.args.get("key") != SECRET:
        abort(403)
    update_labels.main()
    return "✅ Labels updated."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
