"""Login tokens cached between runs, so the sync doesn't log in from scratch nightly.

The workflow keeps .tokens/ in the Actions cache. In a public repo, pull
request workflows can restore that cache, so the file is encrypted with the
TOKEN_CACHE_KEY secret. Without the secret nothing is cached.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from common import REPO_ROOT

CACHE_FILE = REPO_ROOT / ".tokens" / "tokens.enc"


def _fernet(secret: str) -> Fernet:
    key = hashlib.scrypt(
        secret.encode(), salt=b"activity-cards-token-cache", n=2**14, r=8, p=1, dklen=32
    )
    return Fernet(base64.urlsafe_b64encode(key))


def load(secret: str | None, path: Path = CACHE_FILE) -> dict:
    if not secret or not path.exists():
        return {}
    try:
        return json.loads(_fernet(secret).decrypt(path.read_bytes()))
    except (InvalidToken, ValueError):
        print("Token cache could not be decrypted; ignoring it.")
        return {}


def save(tokens: dict, secret: str | None, path: Path = CACHE_FILE) -> None:
    if not secret:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_fernet(secret).encrypt(json.dumps(tokens).encode()))
