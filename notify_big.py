import os
from flask import Blueprint, jsonify, abort
from supabase_utils import get_client
from email_utils import send_email

notify_bp = Blueprint("notify_big", __name__)
supabase = get_client()

@notify_bp.route("/api/notify-big", methods=["POST"])
def notify_big():
    # optional auth
    secret = os.environ.get("UPDATE_SECRET")
    auth = request.headers.get("Authorization", "")
    if secret and (not auth.startswith("Bearer ") or auth.split("Bearer ")[1] != secret):
        abort(403)

    res = supabase.table("notifications").select("*").eq("is_big", True).eq("sent", False).execute()
    data = res.data or []
    sent_count = 0

    for n in data:
        title = n.get("title", "Notification")
        message = n.get("message", "")
        html = f"""
        <div style='font-family:sans-serif;padding:20px'>
          <h2 style='color:#3B82F6'>{title}</h2>
          <p>{message}</p>
          <p><small>Tab: {n.get('tab','General')}</small></p>
          <hr><p style='color:#888'>Hubbalicious Portal Notification</p>
        </div>
        """
        try:
            send_email(f"[Hubbalicious] {title}", html)
            supabase.table("notifications").update({"sent": True}).eq("id", n["id"]).execute()
            sent_count += 1
        except Exception as e:
            print(f"⚠️ Failed to send {title}: {e}")

    return jsonify({"sent": sent_count})
