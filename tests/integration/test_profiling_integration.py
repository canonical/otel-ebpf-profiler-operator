import pytest
import jubilant
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed

from conftest import (
    APP_NAME,
    OTEL_COLLECTOR_APP_NAME,
    COS_CHANNEL,
    APP_BASE,
    patch_otel_collector_log_level,
)
from assertions import assert_pattern_in_snap_logs

# patch the update-status-hook-interval because if the otel collector charm handles an event, it will regenerate its config and overwrite the config patch
pytestmark = pytest.mark.usefixtures("patch_update_status_interval")


@pytest.mark.setup
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
def test_deploy_otel_collector(juju: Juju):
    juju.deploy(OTEL_COLLECTOR_APP_NAME, channel=COS_CHANNEL, base=APP_BASE)


@pytest.mark.setup
def test_integrate_profiling(juju: Juju):
    juju.integrate(f"{APP_NAME}:cos-agent", OTEL_COLLECTOR_APP_NAME)
    juju.integrate(f"{APP_NAME}:profiling", OTEL_COLLECTOR_APP_NAME)

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


@retry(stop=stop_after_attempt(10), wait=wait_fixed(10))
def test_profiles_are_pushed(juju: Juju):
    grep_filters = [
        '"otelcol.signal": "profiles"',
        '"resource profiles"',
        '"sample records"',
    ]
    assert_pattern_in_snap_logs(juju, grep_filters)
