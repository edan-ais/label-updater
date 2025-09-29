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

    summary = update_labels.main()

    # Format summary nicely for browser
    html = ["<h2>✅ Labels updated</h2>", "<ul>"]
    for name, status, date in summary:
        if status == "updated":
            html.append(f"<li>{name}: updated → {date}</li>")
        else:
            html.append(f"<li>{name}: no matches found</li>")
    html.append("</ul>")

    return "\n".join(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
