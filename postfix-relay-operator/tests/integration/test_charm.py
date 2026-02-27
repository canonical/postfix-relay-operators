#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import base64
import hashlib
import logging
import os
import smtplib
import socket
import ssl
import time
from typing import cast

import jubilant
import pytest
import requests
import yaml

logger = logging.getLogger(__name__)

TLS_RELATION_CERT_PATH = "/etc/postfix/tls/fullchain.pem"


def _exec_stdout(result) -> str:
    if hasattr(result, "stdout"):
        return result.stdout
    if isinstance(result, bytes):
        return result.decode("utf-8")
    if isinstance(result, str):
        return result
    return str(result)


def _first_pem_certificate(pem_text: str) -> str:
    begin_marker = "-----BEGIN CERTIFICATE-----"
    end_marker = "-----END CERTIFICATE-----"
    start = pem_text.find(begin_marker)
    if start == -1:
        raise AssertionError("No certificate found in relation TLS bundle.")
    end = pem_text.find(end_marker, start)
    if end == -1:
        raise AssertionError("Certificate end marker missing in relation TLS bundle.")
    return pem_text[start : (end + len(end_marker))]  # noqa: E203


def _sha256_fingerprint_from_pem(pem_text: str) -> str:
    der_bytes = ssl.PEM_cert_to_DER_cert(_first_pem_certificate(pem_text))
    return hashlib.sha256(der_bytes).hexdigest()


def sha512(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(8)
    digest = hashlib.sha512(password.encode("utf-8") + salt).digest()
    b64 = base64.b64encode(digest + salt).decode("ascii")
    return "{SSHA512}" + b64


@pytest.fixture(scope="session", name="machine_ip_address")
def machine_ip_address_fixture() -> str:
    """IP address for the machine running the tests."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_address = s.getsockname()[0]
    logger.info("IP Address for the current test runner: %s", ip_address)
    s.close()
    return ip_address


@pytest.mark.abort_on_fail
def test_simple_relay(juju: jubilant.Juju, postfix_relay_app, machine_ip_address):
    """
    arrange: Deploy postfix-relay charm with the testrelay.internal domain in relay domains.
    act: Send an email to an address with the testrelay.internal domain.
    assert: The email is correctly relayed to the mailcatcher local test smtp server.
    """
    status = juju.status()
    unit = list(status.apps[postfix_relay_app].units.values())[0]
    unit_ip = unit.public_address

    command_to_put_domain = (
        f"echo {machine_ip_address} testrelay.internal | sudo tee -a /etc/hosts"
    )
    juju.exec(machine=unit.machine, command=command_to_put_domain)

    juju.config(postfix_relay_app, {"relay_domains": "- testrelay.internal"})
    juju.wait(
        lambda status: status.apps[postfix_relay_app].is_active,
        error=jubilant.any_blocked,
        timeout=6 * 60,
    )

    mailcatcher_url = "http://127.0.0.1:1080/messages"
    messages = requests.get(mailcatcher_url, timeout=5).json()
    # There should not be any message in mailcatcher before the test.
    assert len(messages) == 0

    with smtplib.SMTP(unit_ip) as server:
        server.set_debuglevel(2)
        from_addr = "Some One <someone@testrelay.internal>"
        to_addrs = ["otherone@testrelay.internal"]
        server.sendmail(from_addr=from_addr, to_addrs=to_addrs, msg="Hello World!")

    for _ in range(5):
        messages = requests.get(mailcatcher_url, timeout=5).json()
        if messages:
            break
        time.sleep(1)
    assert len(messages) == 1

    # Clean up mailcatcher
    requests.delete(f"{mailcatcher_url}/{messages[0]['id']}", timeout=5)


@pytest.mark.abort_on_fail
def test_authentication(juju: jubilant.Juju, postfix_relay_app, machine_ip_address):
    """
    arrange: Deploy postfix-relay charm with SMTP authentication enabled and a test user.
    act: Attempt to send an email without authentication then with authentication.
    assert: Unauthenticated email sending is refused, authenticated email sending is accepted
    """
    status = juju.status()
    unit = list(status.apps[postfix_relay_app].units.values())[0]
    unit_ip = unit.public_address
    mailcatcher_url = "http://127.0.0.1:1080"

    username = "testuser"
    password = "testpassword"  # nosec
    hashed_password = sha512(password)
    auth_users_yaml = yaml.dump([f"{username}:{hashed_password}"])

    juju.config(
        postfix_relay_app,
        {
            "enable_smtp_auth": "true",
            "smtp_auth_users": auth_users_yaml,
            "relay_host": f"[{machine_ip_address}]",
            "enable_reject_unknown_sender_domain": "false",
        },
    )

    juju.wait(
        lambda s: s.apps[postfix_relay_app].is_active,
        error=jubilant.any_blocked,
        timeout=5 * 60,
    )

    # Unauthenticated send refused
    with pytest.raises(smtplib.SMTPRecipientsRefused):
        with smtplib.SMTP(unit_ip, 587, timeout=10) as server:
            server.starttls()
            server.sendmail(
                from_addr="unauthenticated@example.com",
                to_addrs=["recipient@example.com"],
                msg="Subject: Auth Fail Test",
            )

    requests.delete(f"{mailcatcher_url}/messages", timeout=5)

    # Authenticated send succeed
    with smtplib.SMTP(unit_ip, 587, timeout=10) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(
            from_addr="authenticated@example.com",
            to_addrs=["recipient@example.com"],
            msg="Subject: Auth Success Test",
        )

    messages = []
    for _ in range(5):
        messages = requests.get(f"{mailcatcher_url}/messages", timeout=5).json()
        if messages:
            break
        time.sleep(1)
    assert len(messages) == 1
    assert messages[0]["recipients"] == ["<recipient@example.com>"]

    # Clean up mailcatcher
    requests.delete(f"{mailcatcher_url}/messages/{messages[0]['id']}", timeout=5)


@pytest.mark.abort_on_fail
def test_metrics_configured(juju: jubilant.Juju, postfix_relay_app, machine_ip_address):
    """
    arrange: Deploy postfix-relay.
    act: Get the metrics from the unit.
    assert: The metrics can be scraped and there are metrics.
    """
    juju.wait(
        lambda status: status.apps[postfix_relay_app].is_active,
        timeout=5 * 60,
        delay=30,
    )
    status = juju.status()
    unit = list(status.apps[postfix_relay_app].units.values())[0]
    unit_ip = unit.public_address

    metrics_output = requests.get(f"http://{unit_ip}:9103/metrics", timeout=5).text
    # Some of the most important metrics used in the dashboard and alerts.
    expected_metrics = [
        "cpu_usage_idle",
        "postfix_queue_length",
        "procstat_lookup_running",
        "netstat_tcp_established",
    ]
    for expected_metric in expected_metrics:
        assert expected_metric in metrics_output


@pytest.mark.abort_on_fail
def test_tls_uses_relation_certificate(juju: jubilant.Juju, postfix_relay_app):
    """
    arrange: Postfix-relay is related to a TLS certificate provider.
    act: Connect with STARTTLS and read the presented server certificate.
    assert: The certificate fingerprint matches the relation-provided fullchain.
    """
    status = juju.status()
    unit = list(status.apps[postfix_relay_app].units.values())[0]
    unit_ip = unit.public_address

    pem_result = juju.exec(
        machine=unit.machine,
        command=f"sudo cat {TLS_RELATION_CERT_PATH}",
    )
    pem_text = _exec_stdout(pem_result)
    assert "BEGIN CERTIFICATE" in pem_text

    with smtplib.SMTP(unit_ip, 587, timeout=10) as server:
        server.starttls()
        peer_der = cast(ssl.SSLSocket, server.sock).getpeercert(binary_form=True)

    assert peer_der
    peer_fingerprint = hashlib.sha256(peer_der).hexdigest()
    relation_fingerprint = _sha256_fingerprint_from_pem(pem_text)
    assert peer_fingerprint == relation_fingerprint
