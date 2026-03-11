"""Load and save CLI configuration from ~/.criblrc."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from cribl_cli.config.types import AuthType, CriblConfig, CriblRc, ProfileConfig

RC_PATH = Path.home() / ".criblrc"


def load_rc(path: Path | None = None) -> CriblRc:
    rc_file = path or RC_PATH
    try:
        raw = json.loads(rc_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return CriblRc()

    profiles: dict[str, ProfileConfig] = {}
    for name, data in raw.get("profiles", {}).items():
        profiles[name] = ProfileConfig(
            base_url=data.get("baseUrl", ""),
            auth_type=data.get("authType", "cloud"),
            client_id=data.get("clientId"),
            client_secret=data.get("clientSecret"),
            username=data.get("username"),
            password=data.get("password"),
        )
    return CriblRc(
        profiles=profiles,
        active_profile=raw.get("activeProfile", "default"),
    )


def save_rc(rc: CriblRc, path: Path | None = None) -> None:
    rc_file = path or RC_PATH
    profiles_raw: dict = {}
    for name, p in rc.profiles.items():
        d: dict = {"baseUrl": p.base_url, "authType": p.auth_type}
        if p.client_id:
            d["clientId"] = p.client_id
        if p.client_secret:
            d["clientSecret"] = p.client_secret
        if p.username:
            d["username"] = p.username
        if p.password:
            d["password"] = p.password
        profiles_raw[name] = d

    data = {"profiles": profiles_raw, "activeProfile": rc.active_profile}
    rc_file.write_text(json.dumps(data, indent=2) + "\n")
    rc_file.chmod(0o600)


def load_config(
    profile: str | None = None,
    base_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> CriblConfig:
    rc = load_rc()
    profile_name = profile or os.environ.get("CRIBL_PROFILE") or rc.active_profile
    saved = rc.profiles.get(profile_name, ProfileConfig())

    url = base_url or os.environ.get("CRIBL_BASE_URL") or saved.base_url
    cid = client_id or os.environ.get("CRIBL_CLIENT_ID") or saved.client_id
    csec = client_secret or os.environ.get("CRIBL_CLIENT_SECRET") or saved.client_secret
    user = username or os.environ.get("CRIBL_USERNAME") or saved.username
    pw = password or os.environ.get("CRIBL_PASSWORD") or saved.password

    # Auto-detect auth type
    auth_type: AuthType = "cloud"
    if user and pw and not (cid and csec):
        auth_type = "local"
    elif cid and csec:
        auth_type = "cloud"
    else:
        auth_type = saved.auth_type

    if url:
        parsed = urlparse(url)
        if not parsed.scheme:
            raise ValueError(f"Invalid base URL (missing scheme): {url}")

    if not url:
        raise ValueError(
            "No base URL configured. Run `cribl config set` or set CRIBL_BASE_URL."
        )

    return CriblConfig(
        profile=profile_name,
        base_url=url.rstrip("/"),
        auth_type=auth_type,
        client_id=cid,
        client_secret=csec,
        username=user,
        password=pw,
    )
