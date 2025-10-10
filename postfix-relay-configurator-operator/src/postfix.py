# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postfix Service Layer."""

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import utils
from state import PostfixLookupTableType

if TYPE_CHECKING:
    from pydantic import IPvAnyNetwork

    from state import State


def smtpd_relay_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP relay restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    relay_restrictions = ["permit_mynetworks"]
    if bool(charm_state.relay_access_sources):
        relay_restrictions.append("check_client_access cidr:/etc/postfix/relay_access")

    if charm_state.enable_smtp_auth:
        if charm_state.sender_login_maps:
            relay_restrictions.append("reject_known_sender_login_mismatch")
        if charm_state.restrict_senders:
            relay_restrictions.append("reject_sender_login_mismatch")
        relay_restrictions.append("permit_sasl_authenticated")

    relay_restrictions.append("defer_unauth_destination")

    return relay_restrictions


def smtpd_sender_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP sender restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    sender_restrictions = []
    if charm_state.enable_reject_unknown_sender_domain:
        sender_restrictions.append("reject_unknown_sender_domain")
    sender_restrictions.append("check_sender_access hash:/etc/postfix/access")
    if charm_state.restrict_sender_access:
        sender_restrictions.append("reject")

    return sender_restrictions


def smtpd_recipient_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP recipient restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    recipient_restrictions = []
    if charm_state.append_x_envelope_to:
        recipient_restrictions.append(
            "check_recipient_access regexp:/etc/postfix/append_envelope_to_header"
        )

    if charm_state.restrict_senders:
        recipient_restrictions.append("check_sender_access hash:/etc/postfix/restricted_senders")
    recipient_restrictions.extend(charm_state.additional_smtpd_recipient_restrictions)

    if charm_state.enable_spf:
        recipient_restrictions.append("check_policy_service unix:private/policyd-spf")

    return recipient_restrictions


def construct_postfix_config_params(  # pylint: disable=too-many-arguments
    *,
    charm_state: "State",
    fqdn: str,
    hostname: str,
) -> dict[str, str | int | bool | None]:
    """Prepare the context for rendering Postfix configuration files.

    Args:
        charm_state: The current state of the charm.
        fqdn: Fully Qualified Domain Name of the system.
        hostname: Hostname of the system.

    Returns:
        str: The context for remndering Postfix configuration file content.
    """
    return {
        "JUJU_HEADER": utils.JUJU_HEADER,
        "fqdn": fqdn,
        "hostname": hostname,
        "connection_limit": charm_state.connection_limit,
        "enable_rate_limits": charm_state.enable_rate_limits,
        "enable_sender_login_map": bool(charm_state.sender_login_maps),
        "enable_smtp_auth": charm_state.enable_smtp_auth,
        "enable_spf": charm_state.enable_spf,
        "enable_tls_policy_map": bool(charm_state.tls_policy_maps),
        "header_checks": bool(charm_state.header_checks),
        "mynetworks": ",".join(charm_state.allowed_relay_networks),
        "relayhost": charm_state.relay_host,
        "relay_domains": " ".join(charm_state.relay_domains),
        "relay_recipient_maps": bool(charm_state.relay_recipient_maps),
        "restrict_recipients": bool(charm_state.restrict_recipients),
        "smtp_header_checks": bool(charm_state.smtp_header_checks),
        "smtpd_recipient_restrictions": ", ".join(smtpd_recipient_restrictions(charm_state)),
        "smtpd_relay_restrictions": ", ".join(smtpd_relay_restrictions(charm_state)),
        "smtpd_sender_restrictions": ", ".join(smtpd_sender_restrictions(charm_state)),
        "tls_ciphers": charm_state.tls_ciphers.value if charm_state.tls_ciphers else None,
        "tls_exclude_ciphers": ", ".join(charm_state.tls_exclude_ciphers),
        "tls_protocols": " ".join(charm_state.tls_protocols),
        "tls_security_level": (
            charm_state.tls_security_level.value if charm_state.tls_security_level else None
        ),
        "transport_maps": bool(charm_state.transport_maps),
        "virtual_alias_domains": " ".join(charm_state.virtual_alias_domains),
        "virtual_alias_maps": bool(charm_state.virtual_alias_maps),
        "virtual_alias_maps_type": charm_state.virtual_alias_maps_type.value,
    }


class PostfixMap(NamedTuple):
    """Represents a Postfix lookup table and its source file content.

    Attributes:
        type: The type of the Postfix lookup table (e.g., 'hash').
        path: The path to the map's source file.
        content: The content to be written to the map's source file.
        source: The Postfix lookup table source string
    """

    type: PostfixLookupTableType
    path: Path
    content: str

    @property
    def source(self) -> str:
        """Return the full Postfix lookup table source string."""
        return f"{self.type.value}:{self.path}"


def build_postfix_maps(postfix_conf_dir: str, charm_state: "State") -> dict[str, PostfixMap]:
    """Ensure various postfix files exist and are up-to-date with the current charm state.

    Args:
        postfix_conf_dir: directory where postfix config files are stored.
        charm_state: current charm state.

    Returns:
        A dictionary mapping map names to the generated PostfixMap objects.
    """
    postfix_conf_dir_path = Path(postfix_conf_dir)

    def _create_map(type_: str | PostfixLookupTableType, name: str, content: str) -> PostfixMap:
        type_ = (
            type_ if isinstance(type_, PostfixLookupTableType) else PostfixLookupTableType(type_)
        )
        return PostfixMap(
            type=type_,
            path=postfix_conf_dir_path / name,
            content=f"{utils.JUJU_HEADER}\n{content}\n",
        )

    # Create a map of all the maps we may need to create/update from the charm state.
    maps = {
        "append_envelope_to_header": _create_map(
            PostfixLookupTableType.REGEXP,
            "append_envelope_to_header",
            "/^(.*)$/ PREPEND X-Envelope-To: $1",
        ),
        "header_checks": _create_map(
            PostfixLookupTableType.REGEXP,
            "header_checks",
            ";".join(charm_state.header_checks),
        ),
        "relay_access_sources": _create_map(
            PostfixLookupTableType.CIDR,
            "relay_access",
            "\n".join(charm_state.relay_access_sources),
        ),
        "relay_recipient_maps": _create_map(
            PostfixLookupTableType.HASH,
            "relay_recipient",
            "\n".join(
                [f"{key} {value}" for key, value in charm_state.relay_recipient_maps.items()]
            ),
        ),
        "restrict_recipients": _create_map(
            PostfixLookupTableType.HASH,
            "restricted_recipients",
            "\n".join(
                [f"{key} {value.value}" for key, value in charm_state.restrict_recipients.items()]
            ),
        ),
        "restrict_senders": _create_map(
            PostfixLookupTableType.HASH,
            "restricted_senders",
            "\n".join(
                [f"{key} {value.value}" for key, value in charm_state.restrict_senders.items()]
            ),
        ),
        "sender_access": _create_map(
            PostfixLookupTableType.HASH,
            "access",
            "".join([f"{domain:35} OK\n" for domain in charm_state.restrict_sender_access]),
        ),
        "sender_login_maps": _create_map(
            PostfixLookupTableType.HASH,
            "sender_login",
            "\n".join([f"{key} {value}" for key, value in charm_state.sender_login_maps.items()]),
        ),
        "smtp_header_checks": _create_map(
            PostfixLookupTableType.REGEXP,
            "smtp_header_checks",
            ";".join(charm_state.smtp_header_checks),
        ),
        "tls_policy_maps": _create_map(
            PostfixLookupTableType.HASH,
            "tls_policy",
            "\n".join([f"{key} {value}" for key, value in charm_state.tls_policy_maps.items()]),
        ),
        "transport_maps": _create_map(
            PostfixLookupTableType.HASH,
            "transport",
            "\n".join([f"{key} {value}" for key, value in charm_state.transport_maps.items()]),
        ),
        "virtual_alias_maps": _create_map(
            charm_state.virtual_alias_maps_type.value,
            "virtual_alias",
            "\n".join([f"{key} {value}" for key, value in charm_state.virtual_alias_maps.items()]),
        ),
    }

    return maps


def construct_policyd_spf_config_file_content(spf_skip_addresses: "list[IPvAnyNetwork]") -> str:
    """Generate the configuration content for the policyd-spf service.

    Args:
        spf_skip_addresses: A list of IP addresses or networks to exclude from SPF checks.

    Returns:
        str: The rendered configuration file content for policyd-spf.
    """
    context = {
        "JUJU_HEADER": utils.JUJU_HEADER,
        "skip_addresses": ",".join([str(address) for address in spf_skip_addresses]),
    }
    return utils.render_jinja2_template(context, "templates/policyd_spf_conf.tmpl")
