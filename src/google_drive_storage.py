"""Private Google Drive storage for report attachments.

Credentials are read exclusively from environment variables.  The application
uses the narrow ``drive.file`` OAuth scope, so it can access only files that it
created for this integration.
"""

import io
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload


REQUIRED_ENV = (
    "GOOGLE_DRIVE_FOLDER_ID",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
)
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"


def drive_enabled():
    return all(os.getenv(name, "").strip() for name in REQUIRED_ENV)


def _service():
    if not drive_enabled():
        raise RuntimeError("Google Drive storage is not configured")
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=[DRIVE_FILE_SCOPE],
    )
    credentials.refresh(Request())
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_file(content, filename, mime_type):
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
    metadata = {
        "name": filename,
        "parents": [os.environ["GOOGLE_DRIVE_FOLDER_ID"]],
    }
    created = _service().files().create(
        body=metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return created["id"]


def download_file(file_id):
    request = _service().files().get_media(fileId=file_id, supportsAllDrives=True)
    output = io.BytesIO()
    downloader = MediaIoBaseDownload(output, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return output.getvalue()
