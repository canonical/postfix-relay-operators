# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--charm-file", action="store", help="Charm file to be deployed")
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="No-op; kept for CI compatibility. Use --no-juju-teardown instead.",
    )
