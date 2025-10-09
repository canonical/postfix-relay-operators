#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Postfix Relay Configurator charm."""

import logging
import socket
from pathlib import Path
from typing import Any

import ops

import utils
from dovecot import (
    construct_dovecot_config_file_content,
    construct_dovecot_user_file_content,
)
from postfix import (
    PostfixMap,
    build_postfix_maps,
    construct_policyd_spf_config_file_content,
    construct_postfix_config_params,
)
from state import ConfigurationError, State
from tls import get_tls_config_paths

logger = logging.getLogger(__name__)

TEMPLATES_DIRPATH = Path("templates")
FILES_DIRPATH = Path("files")

POSTFIX_CONF_DIRPATH = Path("/etc/postfix")
ALIASES_FILEPATH = Path("/etc/aliases")
POLICYD_SPF_FILEPATH = Path("/etc/postfix-policyd-spf-python/policyd-spf.conf")
TLS_DH_PARAMS_FILEPATH = Path("/etc/ssl/private/dhparams.pem")
MAIN_CF = "main.cf"
MAIN_CF_TMPL = "postfix_main_cf.tmpl"
MASTER_CF = "master.cf"
MASTER_CF_TMPL = "postfix_master_cf.tmpl"

DOVECOT_NAME = "dovecot"
DOVECOT_CONFIG_FILEPATH = Path("/etc/dovecot/dovecot.conf")
DOVECOT_USERS_FILEPATH = Path("/etc/dovecot/users")

RSYSLOG_CONF_SRC = FILES_DIRPATH / "50-default.conf"
RSYSLOG_CONF_DST = Path("/etc/rsyslog.d/50-default.conf")


class PostfixRelayConfiguratorCharm(ops.CharmBase):
    """Postfix Relay Configurator."""

    def __init__(self, *args: Any) -> None:
        """Postfix Relay Configurator."""
        super().__init__(*args)

        self.framework.observe(self.on.config_changed, self._reconcile)

    def _reconcile(self, _: ops.EventBase) -> None:
        self.unit.status = ops.MaintenanceStatus("Reconciling config")
        try:
            charm_state = State.from_charm(self.config)
        except ConfigurationError:
            logger.exception("Error validating the charm configuration.")
            self.unit.status = ops.BlockedStatus("Invalid config")
            return

        self._configure_auth(charm_state)
        self._configure_relay(charm_state)
        self._configure_policyd_spf(charm_state)
        self.unit.status = ops.ActiveStatus()

    def _configure_auth(self, charm_state: State) -> None:
        """Ensure SMTP authentication is configured or disabled via Dovecot."""
        self.unit.status = ops.MaintenanceStatus("Setting up authentication (dovecot)")

        contents = construct_dovecot_config_file_content(
            DOVECOT_USERS_FILEPATH, charm_state.enable_smtp_auth
        )
        utils.write_file(contents, DOVECOT_CONFIG_FILEPATH)

        if charm_state.smtp_auth_users:
            contents = construct_dovecot_user_file_content(charm_state.smtp_auth_users)
            utils.write_file(contents, DOVECOT_USERS_FILEPATH, perms=0o640, group=DOVECOT_NAME)

    def _generate_fqdn(self, domain: str) -> str:
        return f"{self.unit.name.replace('/', '-')}.{domain}"

    def _configure_relay(self, charm_state: State) -> None:
        """Generate and apply Postfix configuration."""
        self.unit.status = ops.MaintenanceStatus("Setting up Postfix relay")

        tls_config_paths = get_tls_config_paths(TLS_DH_PARAMS_FILEPATH)
        fqdn = self._generate_fqdn(charm_state.domain) if charm_state.domain else socket.getfqdn()
        hostname = socket.gethostname()

        context = construct_postfix_config_params(
            charm_state=charm_state,
            tls_dh_params_path=tls_config_paths.tls_dh_params,
            tls_cert_path=tls_config_paths.tls_cert,
            tls_key_path=tls_config_paths.tls_key,
            tls_cert_key_path=tls_config_paths.tls_cert_key,
            fqdn=fqdn,
            hostname=hostname,
        )
        contents = utils.render_jinja2_template(context, TEMPLATES_DIRPATH / MAIN_CF_TMPL)
        utils.write_file(contents, POSTFIX_CONF_DIRPATH / MAIN_CF)
        contents = utils.render_jinja2_template(context, TEMPLATES_DIRPATH / MASTER_CF_TMPL)
        utils.write_file(contents, POSTFIX_CONF_DIRPATH / MASTER_CF)

        postfix_maps = build_postfix_maps(POSTFIX_CONF_DIRPATH, charm_state)
        self._apply_postfix_maps(list(postfix_maps.values()))

        logger.info("Updating aliases")
        self._update_aliases(charm_state.admin_email)

    @staticmethod
    def _apply_postfix_maps(postfix_maps: list[PostfixMap]) -> None:
        logger.info("Applying postfix maps")
        for postfix_map in postfix_maps:
            utils.write_file(postfix_map.content, postfix_map.path)

    @staticmethod
    def _update_aliases(admin_email: str | None) -> None:

        aliases = []
        if ALIASES_FILEPATH.is_file():
            with ALIASES_FILEPATH.open("r", encoding="utf-8") as f:
                aliases = f.readlines()

        add_devnull = True
        new_aliases = []
        for line in aliases:
            if add_devnull and line.startswith("devnull:"):
                add_devnull = False
            if not line.startswith("root:"):
                new_aliases.append(line)

        if add_devnull:
            new_aliases.append("devnull:       /dev/null\n")
        if admin_email:
            new_aliases.append(f"root:          {admin_email}\n")

        utils.write_file("".join(new_aliases), ALIASES_FILEPATH)

    def _configure_policyd_spf(self, charm_state: State) -> None:
        """Configure Postfix SPF policy server (policyd-spf) based on charm state."""
        self.unit.status = ops.MaintenanceStatus("Configuring Postfix policy server")
        if not charm_state.enable_spf:
            logger.info("Postfix policy server for SPF checking (policyd-spf) disabled")
            return

        logger.info("Setting up Postfix policy server for SPF checking (policyd-spf)")

        contents = construct_policyd_spf_config_file_content(charm_state.spf_skip_addresses)
        utils.write_file(contents, POLICYD_SPF_FILEPATH)


if __name__ == "__main__":  # pragma: nocover
    ops.main(PostfixRelayConfiguratorCharm)
