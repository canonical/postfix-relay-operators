# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for the Postfix Relay charm."""

from pathlib import Path
from unittest.mock import ANY, Mock, call, patch

import ops.testing
import pytest
from ops.testing import Context, State

import charm
from state import ConfigurationError

FILES_PATH = Path(__file__).parent / "files"


@patch("charm.State.from_charm", Mock(side_effect=ConfigurationError("Invalid configuration")))
def test_invalid_config(context: Context[charm.PostfixRelayConfiguratorCharm]) -> None:
    """
    arrange: Invalid charm config.
    act: Run the config-changed event hook on the charm.
    assert: The unit status is set to blocked with the correct error message.
    """
    charm_state = State(config={}, leader=True)

    out = context.run(context.on.config_changed(), charm_state)

    assert out.unit_status == ops.testing.BlockedStatus("Invalid config")


class TestConfigureAuth:
    """Unit tests for _configure_auth."""

    @pytest.mark.parametrize(
        "smtp_auth_users",
        [pytest.param("", id="no auth users"), pytest.param("- user", id="with auth users")],
    )
    @patch("charm.utils.write_file")
    def test_no_auth(
        self,
        mock_write_file: Mock,
        smtp_auth_users: str,
        context: Context[charm.PostfixRelayConfiguratorCharm],
    ) -> None:
        """
        arrange: Charm with SMTP auth disabled.
        act: Run the config-changed event hook on the charm.
        assert: The charm correctly configures dovecot for a disabled state,
            pauses the dovecot service, and does not open SMTP auth ports.
        """
        charm_state = State(
            config={
                "enable_smtp_auth": False,
                "smtp_auth_users": smtp_auth_users,
            },
            leader=True,
        )

        out = context.run(context.on.config_changed(), charm_state)

        expected_write_calls = [call(ANY, charm.DOVECOT_CONFIG_FILEPATH)]
        if smtp_auth_users:
            expected_write_calls.append(
                call(ANY, charm.DOVECOT_USERS_FILEPATH, perms=0o640, group=charm.DOVECOT_NAME)
            )

        mock_write_file.assert_has_calls(expected_write_calls)

        assert out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.utils.write_file")
    def test_with_auth_dovecot(
        self,
        mock_write_file: Mock,
        context: Context[charm.PostfixRelayConfiguratorCharm],
    ) -> None:
        """
        arrange: Charm with SMTP auth enabled and dovecot not running.
        act: Run the config-changed event hook on the charm.
        assert: Opensthe required ports, generates the dovecot config,
            and resumes the dovecot service.
        """
        charm_state = State(config={"enable_smtp_auth": True}, leader=True)

        out = context.run(context.on.config_changed(), charm_state)

        mock_write_file.assert_has_calls([call(ANY, charm.DOVECOT_CONFIG_FILEPATH)])

        assert out.unit_status == ops.testing.ActiveStatus()


@patch.object(
    charm, "construct_postfix_config_params", wraps=charm.construct_postfix_config_params
)
@patch("charm.utils.write_file", Mock())
def test_configure_relay(
    mock_construct_postfix_config_params: Mock,
    context: Context[charm.PostfixRelayConfiguratorCharm],
) -> None:
    """
    arrange: Configure the charm with defaults.
    act: Run the config-changed event hook.
    assert: The charm constructs the correct FQDN.
    """
    charm_state = State(
        config={},
        relations=[],
        leader=True,
    )

    out = context.run(context.on.config_changed(), charm_state)

    mock_construct_postfix_config_params.assert_called_once_with(
        charm_state=ANY,
        hostname=ANY,
    )

    assert out.unit_status == ops.testing.ActiveStatus()


@pytest.mark.parametrize(
    "enable_spf",
    [pytest.param(True, id="enable_spf"), pytest.param(False, id="disable_spf")],
)
@patch("charm.utils.write_file")
def test_configure_policyd_spf(
    mock_write_file: Mock,
    enable_spf: bool,
    context: Context[charm.PostfixRelayConfiguratorCharm],
) -> None:
    """
    arrange: Configure the charm state with SPF enabled or disabled.
    act: Run the config-changed event hook.
    assert: Configured only when SPF is enabled.
    """
    charm_state = State(
        config={
            "enable_spf": enable_spf,
            "spf_skip_addresses": "- 10.0.114.0/24",
        }
    )

    out = context.run(context.on.config_changed(), charm_state)

    investigated_call = call(ANY, charm.POLICYD_SPF_FILEPATH)

    if enable_spf:
        mock_write_file.assert_has_calls([investigated_call])
    else:
        assert investigated_call not in mock_write_file.mock_calls

    assert out.unit_status == ops.testing.ActiveStatus()
