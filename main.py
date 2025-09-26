# ==============================
# main.py
# ==============================
from flask import Flask, jsonify, request
import traceback
import update_labels  # our updated script

app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "ok",
        "message": "Label updater service is running. Use POST /run to trigger."
    })

@app.route("/run", methods=["POST"])
def run_label_updater():
    """
    Trigger the label update process.
    Can be called manually (via cURL) or by a scheduler (Cloud Scheduler → Pub/Sub → Cloud Run).
    """
    try:
        update_labels.main()
        return jsonify({"status": "success", "message": "Label update process completed."})
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Error: {e}\n{error_trace}")
        return jsonify({"status": "error", "message": str(e), "trace": error_trace}), 500

if __name__ == "__main__":
    # Local development only
    app.run(host="0.0.0.0", port=8080, debug=True)
