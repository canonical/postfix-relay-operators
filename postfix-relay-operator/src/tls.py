# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""TLS Management Service Layer."""

import os
import subprocess  # nosec
from typing import NamedTuple


class TLSConfigPaths(NamedTuple):
    """A container for TLS file paths.

    Attributes:
        tls_dh_params: Path to the Diffie-Hellman parameters file.
        tls_cert: Path to the TLS certificate file.
        tls_key: Path to the TLS private key file.
        tls_cert_key: Path to a combined certificate and key file (currently unused).
    """

    tls_dh_params: str
    tls_cert: str
    tls_key: str
    tls_cert_key: str


def get_tls_config_paths(
    tls_dh_params: str,
    relation_cert_path: str | None = None,
    relation_key_path: str | None = None,
) -> TLSConfigPaths:
    """Determine paths for TLS assets.

    Args:
        tls_dh_params: Path to the Diffie-Hellman parameters file.
        relation_cert_path: Path to the tls certification set by the relation.
        relation_key_path: Path to the tls key set by the relation.

    Returns:
        TLSConfigPaths: A named tuple containing paths for TLS assets.

    The relation-provided certificate and key are discovered via
    `relation_cert_path` and `relation_key_path` when provided.
    """
    tls_cert_key = ""
    tls_cert = "/etc/ssl/certs/ssl-cert-snakeoil.pem"
    tls_key = "/etc/ssl/private/ssl-cert-snakeoil.key"
    if (
        relation_cert_path
        and relation_key_path
        and os.path.exists(relation_cert_path)
        and os.path.exists(relation_key_path)
    ):
        tls_cert = relation_cert_path
        tls_key = relation_key_path
    if not os.path.exists(tls_dh_params):
        subprocess.check_call(["openssl", "dhparam", "-out", tls_dh_params, "2048"])  # nosec

    return TLSConfigPaths(
        tls_dh_params=tls_dh_params,
        tls_cert=tls_cert,
        tls_key=tls_key,
        tls_cert_key=tls_cert_key,
    )
