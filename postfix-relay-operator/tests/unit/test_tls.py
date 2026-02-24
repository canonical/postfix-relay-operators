# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""TLS service unit tests."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import tls


class TestGetTlsConfigPaths:
    @pytest.mark.parametrize(
        ("dhparams_exist"),
        [
            pytest.param(False, id="no_dhparams"),
            pytest.param(True, id="with_dhparams"),
        ],
    )
    @patch("tls.subprocess.check_call")
    def test_path_logic_without_autocert(
        self,
        mock_subprocess_call: Mock,
        dhparams_exist: bool,
        tmp_path: Path,
    ) -> None:
        """
        arrange: Given no autocert certificate, check behavior based on DH file existence.
        act: Call get_tls_config_paths.
        assert: Snakeoil paths are returned and openssl is called only when needed.
        """
        dhparams_path = tmp_path / "dhparams.pem"
        if dhparams_exist:
            dhparams_path.touch()

        result = tls.get_tls_config_paths(str(dhparams_path))

        if dhparams_exist:
            mock_subprocess_call.assert_not_called()
        else:
            mock_subprocess_call.assert_called_with(
                ["openssl", "dhparam", "-out", str(dhparams_path), "2048"]
            )

        assert result.tls_cert == "/etc/ssl/certs/ssl-cert-snakeoil.pem"
        assert result.tls_key == "/etc/ssl/private/ssl-cert-snakeoil.key"
        assert result.tls_dh_params == str(dhparams_path)

    @patch("tls.subprocess.check_call")
    def test_relation_paths_preferred(
        self,
        mock_subprocess_call: Mock,
        tmp_path: Path,
    ) -> None:
        """
        arrange: Provide relation cert/key files.
        act: Call get_tls_config_paths with relation file paths.
        assert: Relation files are used and openssl is not called.
        """
        dhparams_path = tmp_path / "dhparams.pem"
        dhparams_path.touch()
        relation_cert = tmp_path / "relation.crt"
        relation_key = tmp_path / "relation.key"
        relation_cert.write_text("cert")
        relation_key.write_text("key")

        result = tls.get_tls_config_paths(
            str(dhparams_path),
            relation_cert_path=str(relation_cert),
            relation_key_path=str(relation_key),
        )

        mock_subprocess_call.assert_not_called()
        assert result.tls_cert == str(relation_cert)
        assert result.tls_key == str(relation_key)
        assert result.tls_dh_params == str(dhparams_path)
