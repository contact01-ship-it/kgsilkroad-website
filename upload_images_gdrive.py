"""
Uploads all images from images/ to Google Drive folder 'peptide-catalog-images',
makes each file public, and saves links to image_links.json.

SETUP (one time):
  1. Go to: https://console.cloud.google.com/
  2. Top bar → select or create a project
  3. Left menu → APIs & Services → Library → search "Google Drive API" → Enable
  4. Left menu → APIs & Services → Credentials → Create Credentials → OAuth client ID
  5. Application type: Desktop app → name it anything → Create
  6. Click "Download JSON" → save as gdrive_credentials.json in this folder
  7. Run: python3 upload_images_gdrive.py
  8. Browser opens → sign in → Allow → done (token cached as gdrive_token.json)

Next runs: just run python3 upload_images_gdrive.py (no browser needed)
"""

import json
import sys
from pathlib import Path

IMAGES_DIR = Path("images")
OUTPUT_FILE = Path("image_links.json")
FOLDER_ID = "1i5dCzuqu7FpqcZjaFAUMbtgZkoonoznh"
TOKEN_FILE = Path("gdrive_token.json")
CREDS_FILE = Path("gdrive_credentials.json")
SCOPES = ["https://www.googleapis.com/auth/drive"]

MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def get_service():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print("Installing required libraries...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
            "google-api-python-client", "google-auth-httplib2", "google-auth-oauthlib"])
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDS_FILE.exists():
                print(f"\n❌ File not found: {CREDS_FILE}")
                print("\nTo set up (5 min, one time):")
                print("  1. https://console.cloud.google.com/")
                print("  2. APIs & Services → Library → 'Google Drive API' → Enable")
                print("  3. APIs & Services → Credentials → Create → OAuth client ID")
                print("  4. Application type: Desktop app → Create → Download JSON")
                print(f"  5. Save the file as: {CREDS_FILE.absolute()}")
                print("  6. Run this script again")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print("✓ Authenticated — token saved to gdrive_token.json")

    return build("drive", "v3", credentials=creds)


def main():
    images = sorted(IMAGES_DIR.iterdir())
    if not images:
        print(f"No images in {IMAGES_DIR}/"); return

    print(f"→ Authenticating...")
    service = get_service()
    print(f"✓ Connected to Google Drive")
    print(f"→ Folder: https://drive.google.com/drive/folders/{FOLDER_ID}")

    # Load existing progress
    results = {}
    if OUTPUT_FILE.exists():
        for item in json.loads(OUTPUT_FILE.read_text()):
            results[item["filename"]] = item
        print(f"→ {len(results)} files already uploaded, resuming...")

    from googleapiclient.http import MediaFileUpload

    total = len(images)
    uploaded = 0
    for i, path in enumerate(images, 1):
        if path.name in results:
            print(f"[{i}/{total}] ✓ skip  {path.name}")
            continue

        ext = path.suffix.lstrip(".").lower()
        mime = MIME_MAP.get(ext, "image/png")
        size_kb = path.stat().st_size // 1024
        print(f"[{i}/{total}] ↑ upload {path.name} ({size_kb}KB)...", end=" ", flush=True)

        try:
            file_meta = {"name": path.name, "parents": [FOLDER_ID]}
            media = MediaFileUpload(str(path), mimetype=mime, resumable=True)
            file = service.files().create(
                body=file_meta, media_body=media, fields="id,name"
            ).execute()
            file_id = file["id"]

            # Make public (anyone with link can view)
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

            results[path.name] = {
                "filename": path.name,
                "file_id": file_id,
                "view_link": f"https://drive.google.com/file/d/{file_id}/view?usp=sharing",
                "direct_link": f"https://drive.google.com/uc?id={file_id}&export=download",
                "thumbnail": f"https://drive.google.com/thumbnail?id={file_id}&sz=w400",
            }
            uploaded += 1
            print(f"✓ {file_id}")

            # Save progress after each file
            OUTPUT_FILE.write_text(
                json.dumps(list(results.values()), ensure_ascii=False, indent=2)
            )
        except Exception as e:
            print(f"✗ ERROR: {e}")

    print(f"\n✓ Done! {uploaded} new files uploaded ({len(results)} total)")
    print(f"  image_links.json: {OUTPUT_FILE.absolute()}")
    print(f"  Drive folder:     https://drive.google.com/drive/folders/{FOLDER_ID}")


if __name__ == "__main__":
    main()
