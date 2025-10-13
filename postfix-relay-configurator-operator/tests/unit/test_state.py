# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""State unit tests."""

from ipaddress import ip_network
from typing import cast

import pytest
import yaml

import state


def test_state():
    """
    arrange: do nothing.
    act: initialize a charm state from valid configuration.
    assert: the state values are parsed correctly.
    """
    charm_config = {
        "additional_smtpd_recipient_restrictions": """
            - reject_non_fqdn_helo_hostname
            - reject_unknown_helo_hostname
        """,
        "append_x_envelope_to": True,
        "enable_reject_unknown_sender_domain": False,
        "enable_spf": True,
        "enable_smtp_auth": False,
        "relay_access_sources": """
            # Reject some made user.
            - 10.10.10.5    REJECT
            - 10.10.10.0/24 OK
        """,
        "relay_domains": """
            - domain.example.com
            - domain2.example.com
        """,
        "relay_host": "smtp.relay",
        "relay_recipient_maps": """
            noreply@mydomain.local: noreply@mydomain.local
        """,
        "restrict_recipients": "mydomain.local: OK",
        "restrict_senders": "mydomain.local: REJECT",
        "restrict_sender_access": """
            - canonical.com
            - ubuntu.com
        """,
        "sender_login_maps": """
            group@example.com: group
            group2@example.com: group2
        """,
        "spf_skip_addresses": """
            - 10.0.114.0/24
            - 10.1.1.0/24
        """,
        "transport_maps": """
            example.com: 'smtp:[mx.example.com]'
            admin.example1.com: 'smtp:[mx.example.com]'
        """,
        "virtual_alias_domains": """
            - mydomain.local
            - mydomain2.local
        """,
        "virtual_alias_maps": """
            /^group@example.net/: group@example.com
            /^group2@example.net/: group2@example.com
        """,
        "virtual_alias_maps_type": "hash",
    }
    charm_state = state.State.from_charm(config=charm_config)

    assert charm_state.additional_smtpd_recipient_restrictions == (
        yaml.safe_load(cast("str", charm_config["additional_smtpd_recipient_restrictions"]))
    )
    assert charm_state.append_x_envelope_to
    assert not charm_state.enable_reject_unknown_sender_domain
    assert charm_state.enable_spf
    assert not charm_state.enable_smtp_auth
    assert charm_state.relay_access_sources == yaml.safe_load(
        cast("str", charm_config["relay_access_sources"])
    )
    assert charm_state.relay_domains == yaml.safe_load(cast("str", charm_config["relay_domains"]))
    assert charm_state.relay_host == charm_config["relay_host"]
    restrict_recipients_raw = yaml.safe_load(cast("str", charm_config["restrict_recipients"]))
    restrict_recipients = {
        key: state.AccessMapValue(value) for key, value in restrict_recipients_raw.items()
    }
    assert charm_state.restrict_recipients == restrict_recipients
    restrict_sender_raw = yaml.safe_load(cast("str", charm_config["restrict_senders"]))
    restrict_senders = {
        key: state.AccessMapValue(value) for key, value in restrict_sender_raw.items()
    }
    assert charm_state.restrict_senders == restrict_senders
    assert charm_state.restrict_sender_access == yaml.safe_load(
        cast("str", charm_config["restrict_sender_access"])
    )
    assert charm_state.sender_login_maps == yaml.safe_load(
        cast("str", charm_config["sender_login_maps"])
    )
    assert charm_state.spf_skip_addresses == [
        ip_network(address)
        for address in yaml.safe_load(cast("str", charm_config["spf_skip_addresses"]))
    ]
    assert charm_state.transport_maps == yaml.safe_load(
        cast("str", charm_config["transport_maps"])
    )
    assert charm_state.virtual_alias_domains == yaml.safe_load(
        cast("str", charm_config["virtual_alias_domains"])
    )
    assert charm_state.virtual_alias_maps == yaml.safe_load(
        cast("str", charm_config["virtual_alias_maps"])
    )
    assert charm_state.virtual_alias_maps_type == state.PostfixLookupTableType.HASH


def test_state_defaults():
    """
    arrange: do nothing.
    act: initialize a charm state from default configuration.
    assert: the state values are parsed correctly.
    """
    charm_config = {
        "append_x_envelope_to": False,
        "enable_reject_unknown_sender_domain": True,
        "enable_spf": False,
        "enable_smtp_auth": True,
        "virtual_alias_maps_type": "hash",
    }
    charm_state = state.State.from_charm(config=charm_config)

    assert charm_state.additional_smtpd_recipient_restrictions == []
    assert not charm_state.append_x_envelope_to
    assert charm_state.enable_reject_unknown_sender_domain
    assert not charm_state.enable_spf
    assert charm_state.enable_smtp_auth
    assert charm_state.relay_access_sources == []
    assert charm_state.relay_domains == []
    assert charm_state.relay_host is None
    assert charm_state.restrict_recipients == {}
    assert charm_state.restrict_senders == {}
    assert charm_state.restrict_sender_access == []
    assert charm_state.sender_login_maps == {}
    assert charm_state.spf_skip_addresses == []
    assert charm_state.transport_maps == {}
    assert charm_state.virtual_alias_domains == []
    assert charm_state.virtual_alias_maps == {}
    assert charm_state.virtual_alias_maps_type == state.PostfixLookupTableType.HASH


def test_state_with_invalid_restrict_recipients():
    """
    arrange: do nothing.
    act: initialize a charm state from invalid configuration.
    assert: an InvalidStateError is raised.
    """
    charm_config = {
        "append_x_envelope_to": False,
        "enable_reject_unknown_sender_domain": True,
        "enable_spf": False,
        "enable_smtp_auth": True,
        "restrict_recipients": "recipient: invalid_value",
        "virtual_alias_maps_type": "hash",
    }
    with pytest.raises(state.ConfigurationError):
        state.State.from_charm(config=charm_config)


def test_state_with_invalid_restrict_senders():
    """
    arrange: do nothing.
    act: initialize a charm state from invalid configuration.
    assert: an InvalidStateError is raised.
    """
    charm_config = {
        "append_x_envelope_to": False,
        "enable_reject_unknown_sender_domain": True,
        "enable_spf": False,
        "enable_smtp_auth": True,
        "restrict_senders": "sender: invalid_value",
        "virtual_alias_maps_type": "hash",
    }
    with pytest.raises(state.ConfigurationError):
        state.State.from_charm(config=charm_config)


def test_state_with_invalid_spf_skip_addresses():
    """
    arrange: do nothing.
    act: initialize a charm state from invalid configuration.
    assert: an InvalidStateError is raised.
    """
    charm_config = {
        "append_x_envelope_to": False,
        "enable_reject_unknown_sender_domain": True,
        "enable_spf": False,
        "enable_smtp_auth": True,
        "spf_skip_addresses": "- 192.0.0.0/33",
        "virtual_alias_maps_type": "hash",
    }
    with pytest.raises(state.ConfigurationError):
        state.State.from_charm(config=charm_config)


def test_state_with_invalid_virtual_alias_maps_type():
    """
    arrange: do nothing.
    act: initialize a charm state from invalid configuration.
    assert: an InvalidStateError is raised.
    """
    charm_config = {
        "append_x_envelope_to": False,
        "enable_reject_unknown_sender_domain": True,
        "enable_spf": False,
        "enable_smtp_auth": True,
        "virtual_alias_maps_type": "invalid",
    }
    with pytest.raises(state.ConfigurationError):
        state.State.from_charm(config=charm_config)
