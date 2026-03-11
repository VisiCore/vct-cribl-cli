"""Configuration type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AuthType = Literal["cloud", "local"]


@dataclass
class ProfileConfig:
    base_url: str = ""
    auth_type: AuthType = "cloud"
    client_id: str | None = None
    client_secret: str | None = None
    username: str | None = None
    password: str | None = None


@dataclass
class CriblConfig(ProfileConfig):
    profile: str = "default"


@dataclass
class CriblRc:
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)
    active_profile: str = "default"
