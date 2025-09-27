```python
# ==============================
# update_labels.py (DEBUG TEST MODE)
# ==============================
import os
from googleapiclient.discovery import build
from google.auth import default

# Authenticate
creds, _ = default(scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=creds)

# === CONFIG: replace with your real test values ===
TEST_FILE_ID = "13EXm4JfUgj_np2Fqx4vUBFaTXSFOubrH"   # sample file
TEST_ARCHIVE_FOLDER_ID = "1Ob6gnf2GazvTxSjqMquxUl1zepmmmzOF"  # Rice Crispy archive folder

def debug_test():
    print("=== DEBUG COPY TEST START ===")
    print(f"File ID: {TEST_FILE_ID}")
    print(f"Archive Folder ID: {TEST_ARCHIVE_FOLDER_ID}")

    # Test 1: copy without parents
    try:
        no_parent_body = {"name": "DEBUG-no-parent.pdf"}
        result1 = drive_service.files().copy(
            fileId=TEST_FILE_ID,
            body=no_parent_body
        ).execute()
        print("✅ Copy without parent succeeded:", result1.get("id"))
    except Exception as e:
        print("❌ Copy without parent failed:", e)

    # Test 2: copy with archive folder
    try:
        with_parent_body = {
            "name": "DEBUG-with-parent.pdf",
            "parents": [TEST_ARCHIVE_FOLDER_ID],
        }
        result2 = drive_service.files().copy(
            fileId=TEST_FILE_ID,
            body=with_parent_body
        ).execute()
        print("✅ Copy with parent succeeded:", result2.get("id"))
    except Exception as e:
        print("❌ Copy with parent failed:", e)

    print("=== DEBUG COPY TEST END ===")

if __name__ == "__main__":
    debug_test()
```
