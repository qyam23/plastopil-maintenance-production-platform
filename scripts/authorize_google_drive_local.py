"""One-time local OAuth helper; never writes credentials to disk."""

import argparse
import html
import json
import logging
import os

from flask import Flask, redirect, request
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow


SCOPE = "https://www.googleapis.com/auth/drive.file"


def create_app(client_file):
    # OAuth permits HTTP only for the loopback callback used by installed apps.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    app = Flask(__name__)
    flow = Flow.from_client_secrets_file(client_file, scopes=[SCOPE])
    flow.redirect_uri = "http://127.0.0.1:8765/callback"

    @app.get("/")
    def begin():
        authorization_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return redirect(authorization_url)

    @app.get("/callback")
    def callback():
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        client_config = json.load(open(client_file, encoding="utf-8"))["installed"]
        payload = html.escape(json.dumps({
            "client_id": credentials.client_id,
            "client_secret": client_config["client_secret"],
            "refresh_token": credentials.refresh_token,
        }))
        return (
            "<!doctype html><html lang='he' dir='rtl'><meta charset='utf-8'>"
            "<title>PLASTOPIL Drive connected</title>"
            "<h1>החיבור ל-Google Drive אושר</h1>"
            "<p>ניתן לחזור לאפליקציה. פרטי הגישה לא מוצגים בדף.</p>"
            f"<textarea id='render-secrets' hidden>{payload}</textarea></html>"
        )

    @app.route("/create-folder", methods=["GET", "POST"])
    def create_folder():
        if request.method == "GET":
            return (
                "<!doctype html><html><form method='post'>"
                "<input type='password' name='client_id' aria-label='client id'>"
                "<input type='password' name='client_secret' aria-label='client secret'>"
                "<input type='password' name='refresh_token' aria-label='refresh token'>"
                "<button type='submit'>Create Drive folder</button></form></html>"
            )
        credentials = Credentials(
            token=None,
            refresh_token=request.form["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=request.form["client_id"],
            client_secret=request.form["client_secret"],
            scopes=[SCOPE],
        )
        credentials.refresh(Request())
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        folder = service.files().create(
            body={"name": "PLASTOPIL Reports Media", "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        return (
            "<!doctype html><html lang='he' dir='rtl'><meta charset='utf-8'>"
            "<h1>תיקיית האפליקציה נוצרה</h1>"
            f"<textarea id='folder-id' hidden>{html.escape(folder['id'])}</textarea></html>"
        )

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client_file")
    args = parser.parse_args()
    logging.getLogger("werkzeug").disabled = True
    create_app(args.client_file).run(host="127.0.0.1", port=8765, debug=False, use_reloader=False)
