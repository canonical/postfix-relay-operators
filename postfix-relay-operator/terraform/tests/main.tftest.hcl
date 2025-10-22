# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "3/edge"
  # renovate: depName="postifx-relay"
  revision = 1
}

run "basic_deploy" {
  assert {
    condition     = module.charm_name.app_name == "postfix-relay"
    error_message = "charm_name app_name did not match expected"
  }
}
