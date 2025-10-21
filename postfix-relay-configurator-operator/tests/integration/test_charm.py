#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
def test_simple_relay_configurator(juju: jubilant.Juju, postfix_relay_configurator_app):
    """
    arrange: deploy postfix-relay-configurator char.
    act: do nothing.
    assert: the charm reaches active status.
    """
    juju.wait(
        lambda status: status.apps[postfix_relay_configurator_app].is_active,
        error=jubilant.any_blocked,
        timeout=6 * 60,
    )
