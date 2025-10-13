# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state."""
import itertools
import logging
from collections.abc import Mapping
from enum import Enum
from typing import Any

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)
from typing_extensions import Annotated

logger = logging.getLogger(__name__)


# RFC-1034 and RFC-2181 compliance REGEX for validating FQDNs
HOSTNAME_REGEX = (
    r"(?=.{1,253})(?!.*--.*)(?:(?!-)(?![0-9])[a-zA-Z0-9-]"
    r"{1,63}(?<!-)\.){1,}(?:(?!-)[a-zA-Z0-9-]{1,63}(?<!-))"
)


class CharmStateBaseError(Exception):
    """Represents an error with charm state."""


class ConfigurationError(CharmStateBaseError):
    """Exception raised when a charm configuration is found to be invalid.

    Attributes:
        msg: Explanation of the error.
    """

    def __init__(self, msg: str):
        """Initialize a new instance of the ConfigurationError exception.

        Args:
            msg: Explanation of the error.
        """
        self.msg = msg


class SmtpTlsCipherGrade(Enum):
    """TLS cipher grade.

    Attributes:
        HIGH: "HIGH"
        MEDIUM: "MEDIUM"
        NULL: "NULL"
        LOW: "LOW"º
        EXPORT: "EXPORT"
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    NULL = "NULL"
    LOW = "LOW"
    EXPORT = "EXPORT"


class SmtpTlsSecurityLevel(Enum):
    """TLS secutiry level.

    Attributes:
        NONE: "none"
        MAY: "may"
        ENCRYPT: "encrypt"
    """

    NONE = "none"
    MAY = "may"
    ENCRYPT = "encrypt"


class PostfixLookupTableType(Enum):
    """Postfix lookup table types.

    Attributes:
        HASH: "hash"
        REGEXP: "regexp"
        CIDR: "cidr"
    """

    HASH = "hash"
    REGEXP = "regexp"
    CIDR = "cidr"


class AccessMapValue(Enum):
    """Postfix access map valid values.

    Attributes:
        OK: "OK"
        REJECT: "REJECT"
        RESTRICTED: "restricted"
    """

    OK = "OK"
    REJECT = "REJECT"
    RESTRICTED = "restricted"


def _parse_map(raw_map: str | None) -> dict[str, str]:
    """Parse map input.

    Returns:
        the parsed map.
    """
    return yaml.safe_load(raw_map) if raw_map else {}


def _parse_access_map(raw_map: str | None) -> dict[str, AccessMapValue]:
    """Parse access map input.

    Args:
        raw_map: the raw map content.

    Returns:
        the parsed map.
    """
    parsed_map = _parse_map(raw_map)
    return {key: AccessMapValue(value) for key, value in parsed_map.items()}


def _parse_list(raw_list: str | None) -> list[str]:
    """Parse list input.

    Args:
        raw_list: the list map content.

    Returns:
        a list of strings.
    """
    return yaml.safe_load(raw_list) if raw_list else []


class State(BaseModel):  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """The Postfix Relay operator charm state.

    Attributes:
        enable_reject_unknown_sender_domain: Reject email when sender's domain cannot be resolved.
        relay_access_sources: List of  entries to restrict access based on CIDR source.
        relay_domains: List of destination domains to relay mail to.
        restrict_recipients: Access map for restrictions by recipient address or domain.
        restrict_senders: Access map for restrictions by sender address or domain.
        relay_host: Postfix relay host to forward mail to.
        relay_recipient_maps: Map that alias mail addresses or domains to
            addresses.
        restrict_sender_access: List of domains, addresses or hosts to restrict relay from.
        sender_login_maps: List of authenticated users that can send mail.
        transport_maps: Map from recipient address to message delivery transport
            or next-hop destination.
        virtual_alias_domains: List of domains for which all addresses are aliased.
        virtual_alias_maps: Map of aliases of mail addresses or domains to other local or
            remote addresses.
        virtual_alias_maps_type: The virtual alias map type.
    """

    model_config = ConfigDict(regex_engine="python-re")  # noqa: DCO063

    enable_reject_unknown_sender_domain: bool
    relay_access_sources: list[str]
    relay_domains: list[Annotated[str, Field(min_length=1)]]
    restrict_recipients: dict[str, AccessMapValue]
    restrict_senders: dict[str, AccessMapValue]
    relay_host: Annotated[str, Field(min_length=1)] | None
    relay_recipient_maps: dict[str, str]
    restrict_sender_access: list[Annotated[str, Field(min_length=1)]]
    sender_login_maps: dict[str, str]
    transport_maps: dict[str, str]
    virtual_alias_domains: list[Annotated[str, Field(min_length=1)]]
    virtual_alias_maps: dict[str, str]
    virtual_alias_maps_type: PostfixLookupTableType

    @classmethod
    def from_charm(cls, config: Mapping[str, Any]) -> "State":
        """Initialize the state from charm.

        Args:
            config: the charm configuration.

        Returns:
            Current charm state.

        Raises:
            ConfigurationError: if invalid state values were encountered.
        """
        try:
            relay_access_sources = _parse_list(config.get("relay_access_sources"))
            relay_domains = _parse_list(config.get("relay_domains"))
            relay_recipient_maps = _parse_map(config.get("relay_recipient_maps"))
            restrict_sender_access = _parse_list(config.get("restrict_sender_access"))
            virtual_alias_domains = _parse_list(config.get("virtual_alias_domains"))
            restrict_recipients = _parse_access_map(config.get("restrict_recipients"))
            restrict_senders = _parse_access_map(config.get("restrict_senders"))
            sender_login_maps = _parse_map(config.get("sender_login_maps"))
            transport_maps = _parse_map(config.get("transport_maps"))
            virtual_alias_maps = _parse_map(config.get("virtual_alias_maps"))

            return cls(
                enable_reject_unknown_sender_domain=config.get(
                    "enable_reject_unknown_sender_domain"
                ),  # type: ignore[arg-type]
                relay_access_sources=relay_access_sources,
                relay_domains=relay_domains,
                relay_host=config.get("relay_host"),
                relay_recipient_maps=relay_recipient_maps,
                restrict_recipients=restrict_recipients,
                restrict_senders=restrict_senders,
                restrict_sender_access=restrict_sender_access,
                sender_login_maps=sender_login_maps,
                transport_maps=transport_maps,
                virtual_alias_domains=virtual_alias_domains,
                virtual_alias_maps=virtual_alias_maps,
                virtual_alias_maps_type=PostfixLookupTableType(
                    config.get("virtual_alias_maps_type")
                ),
            )

        except ValueError as exc:
            raise ConfigurationError("Invalid configuration") from exc
        except ValidationError as exc:
            error_fields = set(
                itertools.chain.from_iterable(error["loc"] for error in exc.errors())
            )
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise ConfigurationError(f"Invalid configuration: {error_field_str}") from exc
