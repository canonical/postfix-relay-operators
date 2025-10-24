# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "postfix_relay_configurator" {
  name  = var.app_name
  model = var.model

  charm {
    name     = "postfix-relay-configurator"
    channel  = var.channel
    revision = var.revision
    base     = var.base
  }

  config             = var.config
  constraints        = var.constraints
  units              = 0
  storage_directives = var.storage
}
