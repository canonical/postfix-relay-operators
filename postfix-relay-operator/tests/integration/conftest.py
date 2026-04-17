# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import socket

import jubilant
import pytest

APP_NAME = "postfix-relay"


def deploy(juju: jubilant.Juju, charm: str) -> None:
    """Deploy postfix-relay and its dependencies.

    Args:
        juju: Jubilant Juju instance.
        charm: Path to the charm file to deploy.
    """
    juju.deploy(f"./{charm}", APP_NAME)
    juju.deploy("self-signed-certificates", channel="latest/edge")
    juju.integrate(APP_NAME, "self-signed-certificates")
    juju.wait(
        lambda status: status.apps[APP_NAME].is_active,
        error=jubilant.any_blocked,
        timeout=10 * 60,
    )


@pytest.fixture(scope="module")
def juju(juju: jubilant.Juju) -> jubilant.Juju:
    """Override juju fixture to set wait timeout."""
    juju.wait_timeout = 10 * 60
    return juju


@pytest.fixture(scope="module")
def postfix_relay_charm(pytestconfig: pytest.Config) -> str:
    """Get value from parameter charm-file."""
    charm = pytestconfig.getoption("--charm-file")
    assert charm, "--charm-file must be set"
    return charm


@pytest.fixture(scope="module")
def postfix_relay_app() -> str:
    """Return the postfix-relay app name."""
    return APP_NAME


@pytest.fixture(scope="module")
def machine_ip_address() -> str:
    """Return IP address for the machine running the tests."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    s.close()
    return ip_address
