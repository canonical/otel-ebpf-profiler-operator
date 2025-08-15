#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from pathlib import Path
from typing import List
import pytest
import jubilant
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed
import yaml
from conftest import APP_NAME, COS_CHANNEL
from pytest_bdd import given, when, then

OTEL_COLLECTOR_APP_NAME = "opentelemetry-collector"
METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
# get the charm os base without the trailing `:architecture` part
APP_BASE = next(iter(METADATA["platforms"])).split(":")[0]


@pytest.fixture(scope="module", autouse=True)
def patch_update_status_interval(juju: Juju):
    # patch the update-status-hook-interval because if the otel collector charm handles an event, it will regenerate its config and overwrite the config patch
    juju.model_config({"update-status-hook-interval": "1h"})
    yield
    juju.model_config(reset="update-status-hook-interval")


def _patch_otel_collector_log_level(juju: Juju, unit_no=0):
    # patch the collector's log level to INFO; we need this so that we can inspect the telemetry being dumped by the `debug` exporter
    juju.ssh(
        f"{OTEL_COLLECTOR_APP_NAME}/{unit_no}",
        f"sudo sed -i 's/level: WARN/level: INFO/' /etc/otelcol/config.d/{OTEL_COLLECTOR_APP_NAME}_{unit_no}.yaml",
    )
    # restart the snap for the updates to take place
    juju.ssh(f"{OTEL_COLLECTOR_APP_NAME}/{unit_no}", "sudo snap restart opentelemetry-collector")


def assert_pattern_in_snap_logs(juju: Juju, grep_filters: List[str]):
    cmd = (
        "sudo snap logs opentelemetry-collector -n=all"
        + " | "
        + " | ".join([f"grep {p}" for p in grep_filters])
    )
    otelcol_logs = juju.ssh(f"{OTEL_COLLECTOR_APP_NAME}/0", command=cmd)
    assert otelcol_logs, f"Filters {grep_filters} not found in the {OTEL_COLLECTOR_APP_NAME} logs"


@pytest.mark.setup
@given("an otel-ebpf-profiler charm is deployed")
def test_deploy_profiler(juju: Juju, charm):
    juju.deploy(charm, APP_NAME, constraints={"virt-type": "virtual-machine"})
    juju.wait(
        lambda status: jubilant.all_active(status, APP_NAME),
        timeout=10 * 60,
        error=lambda status: jubilant.any_error(status, APP_NAME),
        delay=10,
        successes=3,
    )


@pytest.mark.setup
@when("an opentelemetry-collector charm is deployed")
def test_deploy_and_integrate_otel_collector(juju: Juju):
    juju.deploy(OTEL_COLLECTOR_APP_NAME, channel=COS_CHANNEL, base=APP_BASE)


@pytest.mark.setup
@when("integrated with the otel-ebpf-profiler over cos-agent")
def test_integrate_cos_agent(juju: Juju):
    juju.integrate(APP_NAME + ":cos-agent", OTEL_COLLECTOR_APP_NAME + ":cos-agent")
    juju.wait(
        lambda status: jubilant.all_blocked(status, OTEL_COLLECTOR_APP_NAME),
        timeout=10 * 60,
        delay=10,
        successes=3,
    )
    juju.wait(
        lambda status: jubilant.all_active(status, APP_NAME),
        timeout=10 * 60,
        error=lambda status: jubilant.any_error(status, APP_NAME),
        delay=10,
        successes=6,
    )

    # we need to patch the log level to capture the output of the debug exporter
    _patch_otel_collector_log_level(juju)


@then("logs are being scraped by the collector")
@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
def test_logs_are_scraped(juju: Juju):
    grep_filters = [
        "log.file.name=otel-ebpf-profiler.log",
        "log.file.path=/var/log/otel-ebpf-profiler.log",
    ]
    assert_pattern_in_snap_logs(juju, grep_filters)


@then("metrics are being scraped by the collector")
@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
def test_metrics_are_scraped(juju: jubilant.Juju):
    grep_filters = [f"juju_application={APP_NAME}", f"juju_model={juju.model}"]
    assert_pattern_in_snap_logs(juju, grep_filters)


@then("the collector aggregates the profiler's log alert rules")
@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
def test_loki_alerts_are_aggregated(juju: Juju):
    alert_files = juju.ssh(
        f"{OTEL_COLLECTOR_APP_NAME}/0",
        f"find /var/lib/juju/agents/unit-{OTEL_COLLECTOR_APP_NAME}-0/charm/loki_alert_rules -type f",
    )
    assert APP_NAME in alert_files
