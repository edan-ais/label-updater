# ==============================
# update_labels.py (Shared Drive + OAuth, base64 token support + 24h cooldown)
# ==============================
import os
import io
import datetime
import tempfile
import pickle
import base64
import time
import fitz  # PyMuPDF
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ==============================
# OAuth Authentication (Workspace user)
# ==============================
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
TOKEN_B64_FILE = 'token.b64'

# --- Decode token.b64 into token.pickle if needed ---
if os.path.exists(TOKEN_B64_FILE):
    with open(TOKEN_B64_FILE, "rb") as f_in, open(TOKEN_FILE, "wb") as f_out:
        f_out.write(base64.b64decode(f_in.read()))

creds = None

# Load saved token if available and valid
if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 0:
    with open(TOKEN_FILE, 'rb') as token:
        creds = pickle.load(token)

# If no valid credentials, run OAuth flow locally to generate token.pickle
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(creds, token)

drive_service = build('drive', 'v3', credentials=creds)

# ==============================
# Cooldown Utilities
# ==============================
LAST_RUN_FILE = "/tmp/last_run.txt"
COOLDOWN_SECONDS = 24 * 3600  # 24 hours

def can_run_now():
    """Check if enough time has passed since the last run."""
    if not os.path.exists(LAST_RUN_FILE):
        return True
    try:
        with open(LAST_RUN_FILE, "r") as f:
            last_run = float(f.read().strip())
        return (time.time() - last_run) > COOLDOWN_SECONDS
    except Exception:
        return True

def mark_last_run():
    """Update last run timestamp."""
    with open(LAST_RUN_FILE, "w") as f:
        f.write(str(time.time()))

# ==============================
# Google Drive Helpers
# ==============================
def list_files_in_folder(folder_id):
    files = []
    page_token = None
    while True:
        query = f"'{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files

def download_file_to_path(file_id, local_path):
    request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with io.FileIO(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

def upload_file_replace(file_id, local_path, mimetype="application/pdf"):
    media = MediaFileUpload(local_path, mimetype=mimetype, resumable=True)
    return drive_service.files().update(
        fileId=file_id,
        media_body=media,
        supportsAllDrives=True
    ).execute()

def find_file_in_folder_by_name(folder_id, name):
    safe_name = name.replace('"', '\\"')
    res = drive_service.files().list(
        q=f"'{folder_id}' in parents and name=\"{safe_name}\" and trashed=false",
        fields='files(id, name)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    files = res.get('files', [])
    return files[0] if files else None

def copy_file_to_folder(file_id, new_folder_id, new_name=None):
    file = drive_service.files().get(fileId=file_id, fields='name', supportsAllDrives=True).execute()
    name = new_name if new_name else file['name']

    existing = find_file_in_folder_by_name(new_folder_id, name)
    if existing:
        drive_service.files().delete(fileId=existing['id'], supportsAllDrives=True).execute()

    copied_file = {'name': name, 'parents': [new_folder_id]}
    return drive_service.files().copy(fileId=file_id, body=copied_file, supportsAllDrives=True).execute()

# ==============================
# Date Utilities
# ==============================
def compute_best_by_date(days_ahead):
    target = datetime.date.today() + datetime.timedelta(days=days_ahead)
    first = target.replace(day=1)
    fifteenth = target.replace(day=15)

    # Only consider dates on/after target
    valid_dates = [d for d in [first, fifteenth] if d >= target]

    if not valid_dates:
        # fallback → next month 15th
        next_month = (target.replace(day=1) + datetime.timedelta(days=32)).replace(day=15)
        rounded = next_month
    else:
        # pick the later valid date
        rounded = max(valid_dates)

    return rounded.strftime("%m/%d/%Y")

# ==============================
# PDF Text Replacement
# ==============================
def replace_best_by_text(doc, new_date):
    """
    Replace only the first occurrence of 'Best if Used By:' in a document.
    """
    phrases_to_match = ["Best if used by:", "Best if Used By:"]

    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            for l in b.get("lines", []):
                for s in l.get("spans", []):
                    text = s.get("text", "").strip()
                    if any(text.startswith(p) for p in phrases_to_match):
                        old_text = text
                        new_text = f"Best if Used By: {new_date}"
                        bbox = fitz.Rect(s["bbox"])
                        rotation = 90 if bbox.height > bbox.width else 0

                        # Overlay new text centered in same bbox
                        page.insert_textbox(
                            bbox,
                            new_text,
                            fontname="helv",
                            fontsize=s["size"],
                            color=(0, 0, 0),
                            align=1,   # center
                            rotate=rotation
                        )

                        print(f"Replaced on page {page_num}: '{old_text}' → '{new_text}' (rotation={rotation})")
                        return True   # ✅ stop after first replacement
    return False

# ==============================
# Main Processing Function
# ==============================
def process_labels(UPDATING_LABELS_FOLDER_ID, ARCHIVE_FOLDER_ID, days_until_best_by):
    files = list_files_in_folder(UPDATING_LABELS_FOLDER_ID)
    pdf_files = [f for f in files if f.get('mimeType') == 'application/pdf' or f['name'].lower().endswith('.pdf')]

    target_date = compute_best_by_date(days_until_best_by)
    print(f"\n--- Processing folder {UPDATING_LABELS_FOLDER_ID} (target date {target_date}) ---\n")

    summary = []

    for f in pdf_files:
        file_id = f["id"]
        name = f["name"]
        print(f"Processing: {name} (id: {file_id})")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, name)
            download_file_to_path(file_id, local_path)
            print(" - downloaded original")

            # Archive before editing
            copy_file_to_folder(file_id, ARCHIVE_FOLDER_ID, name)
            print(f" - archived original as {name}")

            doc = fitz.open(local_path)
            replaced = replace_best_by_text(doc, target_date)

            if replaced:
                new_path = local_path + "_updated.pdf"
                doc.save(new_path, deflate=True)
                doc.close()
                os.replace(new_path, local_path)
                upload_file_replace(file_id, local_path)
                print(f" - ✅ updated best-by date to {target_date}\n")
                summary.append((name, "updated", target_date))
            else:
                doc.close()
                print(" - ⚠️ no matches found to replace\n")
                summary.append((name, "no-replace", None))

    return summary

# ==============================
# Folders Configuration
# ==============================
LABEL_CONFIGS = [
    {
        "updating_folder": "14SHHIMLCYh_ylqQ2LqoUdftXgFeJP2O-",  # fudge
        "archive_folder": "1qIxjklSgyruOUybWnCsr8tcCkKNe26iJ",
        "days_until_best_by": 60,
    },
    {
        "updating_folder": "1hpIcA2LwXd8ogizoNERVvrGfTkweLopV",  # wine fudge
        "archive_folder": "1i-CieIFDrlTwl9sggrT4tWt-X2mEgLwj",
        "days_until_best_by": 60,
    },
    {
        "updating_folder": "17MjwKWaRdqxdu8mQ77ygTorw9nH2WpPu",  # rice crispys
        "archive_folder": "1Vj_zSVW8jizFvj9tAr5hJ45L_yXkI6To",
        "days_until_best_by": 75,
    },
]

def main():
    if not can_run_now():
        print("⏸ Skipping run (still in cooldown).")
        return []

    all_summaries = []
    for config in LABEL_CONFIGS:
        result = process_labels(
            UPDATING_LABELS_FOLDER_ID=config["updating_folder"],
            ARCHIVE_FOLDER_ID=config["archive_folder"],
            days_until_best_by=config["days_until_best_by"]
        )
        all_summaries.extend(result)

    mark_last_run()

    # Final combined summary
    print("\n=== Combined Run Summary ===")
    for name, status, date in all_summaries:
        if status == "updated":
            print(f"{name}: updated → {date}")
        else:
            print(f"{name}: no matches found")

    print("=== All folders processed. Exiting updater. ===\n")
    return all_summaries
