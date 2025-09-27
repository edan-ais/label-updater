```python
# ==============================
# update_labels.py
# ==============================
import os
import io
import datetime
import tempfile
import fitz  # PyMuPDF
from googleapiclient.discovery import build
from google.auth import default
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ==============================
# Authenticate to Google Drive (service account)
# ==============================
creds, _ = default(scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=creds)

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
            pageToken=page_token
        ).execute()
        files.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files

def download_file_to_path(file_id, local_path):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.close()

def upload_file_replace(file_id, local_path, mimetype="application/pdf"):
    media = MediaFileUpload(local_path, mimetype=mimetype, resumable=True)
    return drive_service.files().update(
        fileId=file_id,
        media_body=media
    ).execute()

def find_file_in_folder_by_name(folder_id, name):
    safe_name = name.replace('"', '\\"')
    query = f"'{folder_id}' in parents and name = \"{safe_name}\" and trashed=false"
    res = drive_service.files().list(q=query, fields='files(id, name)').execute()
    files = res.get('files', [])
    return files[0] if files else None

def copy_file_to_folder(file_id, new_folder_id, new_name=None):
    file = drive_service.files().get(fileId=file_id, fields='name').execute()
    name = new_name if new_name else file['name']

    existing = find_file_in_folder_by_name(new_folder_id, name)
    if existing:
        drive_service.files().delete(fileId=existing['id']).execute()

    copied_file = {'name': name, 'parents': [new_folder_id]}
    return drive_service.files().copy(fileId=file_id, body=copied_file).execute()

# ==============================
# Date Utilities
# ==============================
def compute_best_by_date(days_ahead):
    target = datetime.date.today() + datetime.timedelta(days=days_ahead)
    first = target.replace(day=1)
    fifteenth = target.replace(day=15)

    dist_first = abs((target - first).days)
    dist_fifteenth = abs((target - fifteenth).days)

    if dist_first < dist_fifteenth:
        rounded = first
    elif dist_fifteenth < dist_first:
        rounded = fifteenth
    else:
        rounded = first if first < fifteenth else fifteenth

    return rounded.strftime("%m/%d/%Y")

# ==============================
# PDF Text Replacement
# ==============================
def replace_best_by_text(doc, new_date):
    replaced = False
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

                        # White out old text
                        page.draw_rect(bbox, color=(1, 1, 1), fill=(1, 1, 1))

                        # Choose text insertion point based on rotation
                        if rotation == 0:
                            x, y = bbox.x0, bbox.y1
                        else:
                            x, y = bbox.x1, bbox.y1

                        page.insert_text(
                            (x, y),
                            new_text,
                            fontname="helv",
                            fontsize=s["size"],
                            color=(0, 0, 0),
                            rotate=rotation
                        )
                        print(f"Replaced on page {page_num}: '{old_text}' → '{new_text}' (rotation={rotation})")
                        replaced = True
    return replaced

# ==============================
# Main Processing Function
# ==============================
def process_labels(UPDATING_LABELS_FOLDER_ID, ARCHIVE_FOLDER_ID, days_until_best_by):
    files = list_files_in_folder(UPDATING_LABELS_FOLDER_ID)
    pdf_files = [
        f for f in files
        if f.get('mimeType') == 'application/pdf' or f['name'].strip().lower().endswith('.pdf')
    ]

    target_date = compute_best_by_date(days_until_best_by)
    print(f"Target best-by date: {target_date}\n")

    summary = []

    for f in pdf_files:
        file_id = f["id"]
        name = f["name"]
        print(f"Processing: {name} (id: {file_id})")

        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = os.path.join(tmpdir, name)
            download_file_to_path(file_id, local_path)
            print(" - downloaded original")

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

    print("\n=== Run summary ===")
    for item in summary:
        print(item)

# ==============================
# Folders Configuration
# ==============================
LABEL_CONFIGS = [
    {
        "updating_folder": "17MjwKWaRdqxdu8mQ77ygTorw9nH2WpPu",  # Rice Crispy
        "archive_folder": "1Vj_zSVW8jizFvj9tAr5hJ45L_yXkI6To",
        "days_until_best_by": 75,
    },
    {
        "updating_folder": "14SHHIMLCYh_ylqQ2LqoUdftXgFeJP2O-",  # Fudge
        "archive_folder": "1qIxjklSgyruOUybWnCsr8tcCkKNe26iJ",
        "days_until_best_by": 60,
    },
    {
        "updating_folder": "1hpIcA2LwXd8ogizoNERVvrGfTkweLopV",  # Wine Fudge
        "archive_folder": "1i-CieIFDrlTwl9sggrT4tWt-X2mEgLwj",
        "days_until_best_by": 60,
    },
]

def main():
    for config in LABEL_CONFIGS:
        process_labels(
            UPDATING_LABELS_FOLDER_ID=config["updating_folder"],
            ARCHIVE_FOLDER_ID=config["archive_folder"],
            days_until_best_by=config["days_until_best_by"]
        )

if __name__ == "__main__":
    main()
```
