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
