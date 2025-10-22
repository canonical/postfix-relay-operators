# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
  # renovate: depName="postifx-relay-configurator"
  revision = 1
}

run "basic_deploy" {
  assert {
    condition     = module.charm_name.app_name == "postfix-relay-configurator"
    error_message = "charm_name app_name did not match expected"
  }
}
