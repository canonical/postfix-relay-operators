# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postfix Service Layer."""

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import utils
from state import PostfixLookupTableType

if TYPE_CHECKING:
    from state import State


def smtpd_relay_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP relay restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    relay_restrictions = []
    if bool(charm_state.relay_access_sources):
        relay_restrictions.append("check_client_access cidr:/etc/postfix/relay_access")

    return relay_restrictions


def smtpd_sender_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP sender restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    sender_restrictions = []
    if charm_state.restrict_sender_access:
        sender_restrictions.append("reject")

    return sender_restrictions


def smtpd_recipient_restrictions(charm_state: "State") -> list[str]:
    """Generate the SMTP recipient restrictions configuration snippet.

    Args:
        charm_state: the charm state.
    """
    recipient_restrictions = []
    if charm_state.restrict_senders:
        recipient_restrictions.append("check_sender_access hash:/etc/postfix/restricted_senders")

    return recipient_restrictions


def construct_postfix_config_params(
    *,
    charm_state: "State",
    hostname: str,
) -> dict[str, str | int | bool | None]:
    """Prepare the context for rendering Postfix configuration files.

    Args:
        charm_state: The current state of the charm.
        hostname: Hostname of the system.

    Returns:
        str: The context for remndering Postfix configuration file content.
    """
    return {
        "JUJU_HEADER": utils.JUJU_HEADER,
        "hostname": hostname,
        "relayhost": charm_state.relay_host,
        "relay_domains": " ".join(charm_state.relay_domains),
        "restrict_recipients": bool(charm_state.restrict_recipients),
        "smtpd_recipient_restrictions": ", ".join(smtpd_recipient_restrictions(charm_state)),
        "smtpd_relay_restrictions": ", ".join(smtpd_relay_restrictions(charm_state)),
        "smtpd_sender_restrictions": ", ".join(smtpd_sender_restrictions(charm_state)),
        "virtual_alias_domains": " ".join(charm_state.virtual_alias_domains),
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
