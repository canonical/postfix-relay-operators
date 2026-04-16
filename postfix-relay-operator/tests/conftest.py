# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--charm-file", action="store", help="Charm file to be deployed")
    parser.addoption("--model", action="store", default=None, help="Juju model to use")
    parser.addoption(
        "--keep-models", action="store_true", default=False, help="Keep models after tests"
    )
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="Use existing Juju controller/model",
    )
