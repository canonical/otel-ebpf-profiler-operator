import pytest
import jubilant
from jubilant import Juju

from conftest import APP_NAME, get_system_arch

PYRO_TESTER_APP_NAME = "pyroscope-tester"
UNINVITED_GUEST = APP_NAME + "guest"


@pytest.mark.setup
def test_deploy(juju: Juju, charm):
    juju.deploy(
        charm, APP_NAME, constraints={"virt-type": "virtual-machine", "arch": get_system_arch()}
    )
    juju.wait(jubilant.all_active, timeout=5 * 60, error=jubilant.any_error, delay=10, successes=3)


@pytest.mark.setup
def test_deploy_second_profiler_same_machine(juju: Juju, charm):
    machine_id = list(juju.status().apps[APP_NAME].units.values())[0].machine
    juju.deploy(charm, UNINVITED_GUEST, to=machine_id, constraints={"arch": get_system_arch()})
    juju.wait(
        lambda status: jubilant.all_blocked(status, UNINVITED_GUEST),
        timeout=5 * 60,
        error=jubilant.any_error,
        delay=10,
        successes=3,
    )


def test_blocked_status(juju: Juju):
    app_status = juju.status().apps[UNINVITED_GUEST].app_status
    assert app_status.current == "blocked"
    assert "is already being profiled" in app_status.message


@pytest.mark.teardown
def test_cleanup(juju):
    juju.remove_application(UNINVITED_GUEST, force=True)
