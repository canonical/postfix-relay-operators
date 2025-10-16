# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postfix service unit tests."""

from pathlib import Path

import postfix
import state
import utils


def test_build_postfix_maps_returns_correct_data() -> None:
    """
    arrange: Define the charm state and expected dictionary of PostfixMap objects.
    act: Call build_postfix_maps.
    assert: The returned dictionary is identical to the expected dictionary.
    """
    charm_config = {
        # Values directly used by the function under test
        "relay_access_sources": "- 192.168.1.0/24",
        "relay_recipient_maps": "user@example.com: OK",
        "restrict_recipients": "bad@example.com: REJECT",
        "restrict_senders": "spammer@example.com: REJECT",
        "restrict_sender_access": "- unwanted.com",
        "sender_login_maps": "sender@example.com: user@example.com",
        "transport_maps": "domain.com: smtp:relay.example.com",
        "virtual_alias_maps": "alias@example.com: real@example.com",
    }
    charm_state = state.State.from_charm(config=charm_config)
    postfix_conf_dir = "/etc/postfix"

    conf_path = Path(postfix_conf_dir)
    expected_maps = {
        "relay_access_sources": postfix.PostfixMap(
            type=state.PostfixLookupTableType.CIDR,
            path=conf_path / "relay_access",
            content=f"{utils.JUJU_HEADER}\n192.168.1.0/24\n",
        ),
        "relay_recipient_maps": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "relay_recipient",
            content=f"{utils.JUJU_HEADER}\nuser@example.com OK\n",
        ),
        "restrict_recipients": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "restricted_recipients",
            content=f"{utils.JUJU_HEADER}\nbad@example.com REJECT\n",
        ),
        "restrict_senders": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "restricted_senders",
            content=f"{utils.JUJU_HEADER}\nspammer@example.com REJECT\n",
        ),
        "sender_access": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "access",
            content=f"{utils.JUJU_HEADER}\n{'unwanted.com':35} OK\n\n",
        ),
        "sender_login_maps": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "sender_login",
            content=f"{utils.JUJU_HEADER}\nsender@example.com user@example.com\n",
        ),
        "transport_maps": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "transport",
            content=f"{utils.JUJU_HEADER}\ndomain.com smtp:relay.example.com\n",
        ),
        "virtual_alias_maps": postfix.PostfixMap(
            type=state.PostfixLookupTableType.HASH,
            path=conf_path / "virtual_alias",
            content=f"{utils.JUJU_HEADER}\nalias@example.com real@example.com\n",
        ),
    }

    maps = postfix.build_postfix_maps(postfix_conf_dir, charm_state)

    assert maps == expected_maps
