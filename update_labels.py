# ==============================
# update_labels.py — Supabase Storage + PyMuPDF backend (1st/15th rounding)
# ==============================
import os
import io
import time
import tempfile
import datetime
import fitz  # PyMuPDF
from typing import List, Tuple
from supabase import create_client, Client

# -------- Config --------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "labels")
ARCHIVE_DIR = os.environ.get("ARCHIVE_DIR", "archive")
COOLDOWN_SECONDS = int(os.environ.get("COOLDOWN_SECONDS", str(24 * 3600)))
LAST_RUN_FILE = "/tmp/last_run.txt"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# -------- Cooldown helpers --------
def can_run_now() -> bool:
    if not os.path.exists(LAST_RUN_FILE):
        return True
    try:
        with open(LAST_RUN_FILE, "r") as f:
            last = float(f.read().strip())
        return (time.time() - last) > COOLDOWN_SECONDS
    except Exception:
        return True

def mark_last_run():
    with open(LAST_RUN_FILE, "w") as f:
        f.write(str(time.time()))

# -------- DB --------
def fetch_products():
    res = supabase.table("products").select("*").order("created_at", desc=False).execute()
    return res.data or []

# -------- Expiration Rule: add days, then snap to 1st/15th --------
def compute_best_by_date(days_ahead: int) -> str:
    target = datetime.date.today() + datetime.timedelta(days=days_ahead)
    y, m, d = target.year, target.month, target.day
    if d <= 1:
        rounded = datetime.date(y, m, 1)
    elif d <= 15:
        rounded = datetime.date(y, m, 15)
    else:
        if m == 12:
            rounded = datetime.date(y + 1, 1, 1)
        else:
            rounded = datetime.date(y, m + 1, 1)
    return rounded.strftime("%m/%d/%Y")

# -------- PDF Editing --------
def replace_best_by_text(doc: fitz.Document, new_date: str) -> bool:
    phrases = ["Best if used by:", "Best if Used By:"]
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict").get("blocks", [])
        for b in blocks:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    txt = s.get("text", "").strip()
                    if any(txt.startswith(p) for p in phrases):
                        new_text = f"Best if Used By: {new_date}"
                        bbox = fitz.Rect(s["bbox"])
                        page.insert_textbox(
                            bbox,
                            new_text,
                            fontname="helv",
                            fontsize=s.get("size", 8),
                            color=(0, 0, 0),
                            align=1
                        )
                        return True
    return False

# -------- Storage Helpers --------
def list_files(product_folder: str):
    resp = supabase.storage.from_(STORAGE_BUCKET).list(product_folder)
    items = resp if isinstance(resp, list) else resp.get("data", [])
    files = [e for e in items if isinstance(e, dict) and e.get("name") and not e["name"].endswith(".keep")]
    return files

def ensure_placeholders(product_folder: str):
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(product_folder + ".keep", io.BytesIO(b""), {"contentType": "text/plain", "upsert": True})
    except Exception:
        pass
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(product_folder + f"{ARCHIVE_DIR}/.keep", io.BytesIO(b""), {"contentType": "text/plain", "upsert": True})
    except Exception:
        pass

def download_file_to_bytes(path: str) -> bytes:
    return supabase.storage.from_(STORAGE_BUCKET).download(path)

def upload_bytes(path: str, data: bytes, content_type: str = "application/pdf", upsert: bool = True):
    supabase.storage.from_(STORAGE_BUCKET).upload(path, io.BytesIO(data), {"contentType": content_type, "upsert": upsert})

def move_to_archive_copy(product_folder: str, filename: str, original_data: bytes):
    dest = f"{product_folder}{ARCHIVE_DIR}/{filename}"
    upload_bytes(dest, original_data, "application/pdf", upsert=True)

# -------- Processing --------
def process_product(product) -> List[Tuple[str, str, str]]:
    folder = product.get("folder_path")
    if not folder:
        return []

    ensure_placeholders(folder)
    entries = list_files(folder)
    pdfs = [e for e in entries if e.get("name", "").lower().endswith(".pdf")]

    target_date = compute_best_by_date(int(product.get("days_out", 60)))
    summary = []

    for f in pdfs:
        filename = f["name"]
        path = f"{folder}{filename}"
        try:
            original_bytes = download_file_to_bytes(path)
        except Exception:
            summary.append((filename, "download-error", None))
            continue

        # Archive original
        try:
            move_to_archive_copy(folder, filename, original_bytes)
        except Exception:
            pass

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = os.path.join(tmpdir, filename)
            with open(tmp_path, "wb") as f_out:
                f_out.write(original_bytes)

            doc = fitz.open(tmp_path)
            if replace_best_by_text(doc, target_date):
                doc.save(tmp_path, deflate=True)
                doc.close()
                with open(tmp_path, "rb") as f_in:
                    updated_bytes = f_in.read()
                try:
                    upload_bytes(path, updated_bytes, "application/pdf", upsert=True)
                    summary.append((filename, "updated", target_date))
                except Exception:
                    summary.append((filename, "upload-error", None))
            else:
                doc.close()
                summary.append((filename, "no-match", None))

    return summary

def main():
    if not can_run_now():
        print("⏸ Skipping run (still in cooldown).")
        return []

    all_summaries: List[Tuple[str, str, str]] = []
    products = fetch_products()

    for product in products:
        if not product.get("folder_path"):
            continue
        result = process_product(product)
        all_summaries.extend(result)

    mark_last_run()

    print("\n=== Combined Run Summary ===")
    for name, status, date in all_summaries:
        if status == "updated":
            print(f"{name}: updated → {date}")
        else:
            print(f"{name}: {status}")
    print("=== All products processed. ===\n")

    return [[n, s, d] for (n, s, d) in all_summaries]
