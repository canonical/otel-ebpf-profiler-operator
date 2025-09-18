import pytest
import jubilant
from jubilant import Juju, all_active, any_error, all_blocked
from tenacity import retry, stop_after_attempt, wait_fixed

from conftest import (
    APP_NAME,
    OTEL_COLLECTOR_APP_NAME,
    COS_CHANNEL,
    APP_BASE,
    patch_otel_collector_log_level,
    get_system_arch,
)
from assertions import assert_pattern_in_snap_logs
from pytest_bdd import given, when, then

SSC_APP_NAME = "ssc"
# patch the update-status-hook-interval because if the otel collector charm handles an event, it will regenerate its config and overwrite the config patch
pytestmark = pytest.mark.usefixtures("patch_update_status_interval")


@pytest.mark.setup
@given("an ebpf profiler charm is deployed on a juju virtual machine")
def test_deploy(juju: Juju, charm):
    juju.deploy(charm, APP_NAME, constraints={"virt-type": "virtual-machine"})
    juju.wait(jubilant.all_active, timeout=5 * 60, error=jubilant.any_error, delay=10, successes=3)


def test_profiler_running(juju: Juju):
    unit_name = list(juju.status().apps[APP_NAME].units.keys())[0]
    out = juju.ssh(
        unit_name,
        'sudo snap services otel-ebpf-profiler | awk \'$2=="enabled" && $3=="active"\'',
    )
    assert out


@pytest.mark.setup
@given("an otel collector charm is deployed on the same machine")
def test_deploy_otel_collector(juju: Juju):
    juju.deploy(
        OTEL_COLLECTOR_APP_NAME,
        channel=COS_CHANNEL,
        base=APP_BASE,
        constraints={"arch": get_system_arch()},
    )
    # to get otelcol deployed and assigned to a machine
    juju.integrate(f"{APP_NAME}:juju-info", OTEL_COLLECTOR_APP_NAME)
    juju.wait(
        lambda status: all_blocked(status, OTEL_COLLECTOR_APP_NAME),
        timeout=10 * 60,
        delay=10,
        successes=3,
    )


@pytest.mark.setup
@given("a certificates provider charm is deployed")
def test_deploy_ssc(juju: Juju):
    juju.deploy("self-signed-certificates", SSC_APP_NAME, constraints={"arch": get_system_arch()})
    juju.wait(
        lambda status: all_active(status, SSC_APP_NAME),
        timeout=10 * 60,
    )


@pytest.mark.setup
@given("the certificates provider charm is integrated with the collector to enable TLS")
def test_integrate_ssc_collector(juju: Juju):
    juju.integrate(f"{OTEL_COLLECTOR_APP_NAME}:receive-server-cert", SSC_APP_NAME)
    juju.wait(
        lambda status: all_blocked(status, OTEL_COLLECTOR_APP_NAME),
        timeout=10 * 60,
        delay=10,
        successes=3,
    )
    juju.wait(
        lambda status: all_active(status, SSC_APP_NAME),
        timeout=10 * 60,
        delay=10,
        successes=3,
    )


@pytest.mark.setup
@given("the certificates provider charm is integrated with the profiler to provide the CA")
def test_integrate_ssc_profiler(juju: Juju):
    juju.integrate(f"{APP_NAME}:receive-ca-cert", SSC_APP_NAME)
    juju.wait(
        lambda status: all_active(status, APP_NAME, SSC_APP_NAME),
        timeout=10 * 60,
        error=lambda status: any_error(status, APP_NAME),
        delay=10,
        successes=3,
    )


@when("the profiler is integrated with the collector over profiling")
def test_integrate_profiling(juju: Juju):
    juju.integrate(f"{APP_NAME}:profiling", OTEL_COLLECTOR_APP_NAME)
    juju.wait(
        lambda status: jubilant.all_blocked(status, OTEL_COLLECTOR_APP_NAME),
        timeout=10 * 60,
        delay=10,
        successes=6,
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


@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
@then("system-wide profiles are successfully pushed to the collector over TLS")
def test_profiles_are_pushed(juju: Juju):
    grep_filters = [
        '"otelcol.component.kind": "exporter"',
        '"otelcol.signal": "profiles"',
        '"resource profiles"',
        '"sample records"',
    ]
    assert_pattern_in_snap_logs(juju, grep_filters)
