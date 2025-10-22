# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

module "postifx_relay" {
  source      = "../terraform"
  app_name    = var.postifx_relay.app_name
  channel     = var.postifx_relay.channel
  config      = var.postifx_relay.config
  model       = var.model
  constraints = var.postifx_relay.constraints
  revision    = var.postifx_relay.revision
  base        = var.postifx_relay.base
  units       = var.postifx_relay.units
}

module "opendkim" {
  source      = "git::ssh://git@github.com/canonical/opendkim//terraform?depth=1&ref=rev7"
  app_name    = var.opendkim.app_name
  channel     = var.opendkim.channel
  config      = var.opendkim.config
  constraints = var.opendkim.constraints
  model       = var.model
  revision    = var.opendkim.revision
  units       = var.opendkim.units
}

resource "juju_integration" "postifx_relay_opendkim" {
  model = var.model

  application {
    name     = module.postifx_relay.app_name
    endpoint = module.postifx_relay.requires.milter
  }

  application {
    name     = module.opendkim.app_name
    endpoint = module.opendkim.provides.milter
  }
}
