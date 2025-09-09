#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import jubilant
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed
from conftest import (
    APP_NAME,
    COS_CHANNEL,
    patch_otel_collector_log_level,
    OTEL_COLLECTOR_APP_NAME,
    APP_BASE,
)
from pytest_bdd import given, when, then
from assertions import assert_pattern_in_snap_logs


# patch the update-status-hook-interval because if the otel collector charm handles an event, it will regenerate its config and overwrite the config patch
pytestmark = pytest.mark.usefixtures("patch_update_status_interval")


def _trigger_update_status_event(juju: Juju, unit_name: str):
    # `jhack fire charm/0 update-status`
    juju.ssh(
        unit_name,
        f"sudo /usr/bin/juju-exec -u {unit_name} "
        "JUJU_DISPATCH_PATH=hooks/update-status "
        f"JUJU_MODEL_NAME={juju.model} "
        f"JUJU_UNIT_NAME={unit_name} "
        f"/var/lib/juju/agents/unit-{unit_name.replace('/', '-')}/charm/dispatch",
    )


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
def test_deploy_otel_collector(juju: Juju):
    # TODO: https://github.com/canonical/opentelemetry-collector-operator/issues/85
    # Workaround — set workload sampling rate to 100%.
    # The collector misclassifies charm traces as workload traces, so this ensures
    # charm traces are not dropped.
    config = {"tracing_sampling_rate_workload": 100}
    juju.deploy(OTEL_COLLECTOR_APP_NAME, channel=COS_CHANNEL, base=APP_BASE, config=config)


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
    patch_otel_collector_log_level(juju)


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


@then("charm traces are pushed to the collector")
@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
def test_charm_traces_are_pushed(juju: Juju):
    # trigger an update-status hook on the charm to force the emission of charm traces
    _trigger_update_status_event(juju, f"{APP_NAME}/0")
    grep_filters = ["ResourceTraces", f"service.name={APP_NAME}", "charm=otel-ebpf-profiler"]
    assert_pattern_in_snap_logs(juju, grep_filters)
