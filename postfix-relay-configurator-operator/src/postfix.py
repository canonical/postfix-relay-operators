# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postfix Service Layer."""

from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import utils
from state import PostfixLookupTableType

if TYPE_CHECKING:
    from state import State


class PostfixMap(NamedTuple):
    """Represents a Postfix lookup table and its source file content.

    Attributes:
        type: The type of the Postfix lookup table (e.g., 'hash').
        path: The path to the map's source file.
        content: The content to be written to the map's source file.
    """

    type: PostfixLookupTableType
    path: Path
    content: str


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
            PostfixLookupTableType.HASH,
            "virtual_alias",
            "\n".join([f"{key} {value}" for key, value in charm_state.virtual_alias_maps.items()]),
        ),
    }

    return maps
