# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper functions for integration tests."""

import base64
import hashlib
import os


def sha512(password: str, salt: bytes | None = None) -> str:
    """Return a SHA-512 hashed password in the {SSHA512} scheme used by Dovecot.

    Args:
        password: Plain-text password to hash.
        salt: Optional salt bytes; random 8 bytes used when not provided.

    Returns:
        Hashed password string prefixed with ``{SSHA512}``.
    """
    if salt is None:
        salt = os.urandom(8)
    digest = hashlib.sha512(password.encode("utf-8") + salt).digest()
    b64 = base64.b64encode(digest + salt).decode("ascii")
    return "{SSHA512}" + b64
