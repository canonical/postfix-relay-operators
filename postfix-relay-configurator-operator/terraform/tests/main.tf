# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "latest/edge"
}

variable "revision" {
  description = "Revision number of the charm."
  type        = number
  default     = null
}

terraform {
  required_providers {
    juju = {
      version = "~> 0.23.0"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

module "postifx_relay_configurator" {
  source   = "./.."
  app_name = "postfix-relay-configurator"
  channel  = var.channel
  model    = "prod-postfix-relay-configurator-example"
  revision = var.revision
}
