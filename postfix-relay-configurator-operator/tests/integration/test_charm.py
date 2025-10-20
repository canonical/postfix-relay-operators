#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import base64
import hashlib
import logging
import os
import socket

import jubilant
import pytest

logger = logging.getLogger(__name__)


def sha512(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(8)
    digest = hashlib.sha512(password.encode("utf-8") + salt).digest()
    b64 = base64.b64encode(digest + salt).decode("ascii")
    return "{SSHA512}" + b64


@pytest.fixture(scope="session", name="machine_ip_address")
def machine_ip_address_fixture() -> str:
    """IP address for the machine running the tests."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    logger.info("IP Address for the current test runner: %s", ip_address)
    s.close()
    return ip_address


@pytest.mark.abort_on_fail
def test_simple_relay_configurator(
    juju: jubilant.Juju, postfix_relay_configurator_app, machine_ip_address
):
    """
    arrange: Deploy postfix-relay charm with the testrelay.internal domain in relay domains.
    act: Send an email to an address with the testrelay.internal domain.
    assert: The email is correctly relayed to the mailcatcher local test smtp server.
    """
    status = juju.status()
    unit = list(status.apps[postfix_relay_configurator_app].units.values())[0]

    command_to_put_domain = (
        f"echo {machine_ip_address} testrelay.internal | sudo tee -a /etc/hosts"
    )
    juju.exec(machine=unit.machine, command=command_to_put_domain)

    juju.wait(
        lambda status: status.apps[postfix_relay_configurator_app].is_active,
        error=jubilant.any_blocked,
        timeout=6 * 60,
    )
