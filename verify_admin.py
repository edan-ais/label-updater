import os
from flask import Blueprint, request, jsonify, abort

verify_bp = Blueprint("verify", __name__)

@verify_bp.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json(force=True)
    code = data.get("code")
    if not code:
        abort(400, "Missing code")
    expected = os.environ.get("ADMIN_ACCESS_CODE")
    if code == expected:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 403
