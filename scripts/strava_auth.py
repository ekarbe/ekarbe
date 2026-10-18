"""One-time helper: print a Strava refresh token for the STRAVA_REFRESH_TOKEN secret.

Run it on your own machine, never in Actions:

    STRAVA_CLIENT_ID=... STRAVA_CLIENT_SECRET=... python scripts/strava_auth.py

It asks for activity:read_all so activities set to "Only me" count too,
the same as they do on Garmin.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from fetch_strava import TIMEOUT_S, TOKEN_URL

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"


def main() -> None:
    client_id = os.environ["STRAVA_CLIENT_ID"]
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "http://localhost/exchange_token",
            "approval_prompt": "force",
            "scope": "activity:read_all",
        }
    )
    print(f"1. Open this URL and click Authorize:\n\n   {AUTHORIZE_URL}?{query}\n")
    print("2. Your browser lands on a localhost page that fails to load. That's expected.")
    pasted = input("3. Paste that page's full URL here: ").strip()
    code = parse_qs(urlparse(pasted).query).get("code", [pasted])[0]

    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=TIMEOUT_S,
    )
    response.raise_for_status()
    print("\nSave this as the STRAVA_REFRESH_TOKEN repository secret:\n")
    print(f"   {response.json()['refresh_token']}")


if __name__ == "__main__":
    main()
