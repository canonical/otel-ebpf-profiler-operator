import pytest
import jubilant
from jubilant import Juju

from conftest import APP_NAME

PYRO_TESTER_APP_NAME = "pyroscope-tester"


@pytest.mark.setup
def test_deploy(juju: Juju, charm):
    juju.deploy(charm, APP_NAME, constraints={"virt-type": "virtual-machine"})
    juju.wait(jubilant.all_active)


def test_profiler_running(juju: Juju):
    unit_name = list(juju.status().apps[APP_NAME].units.keys())[0]
    out = juju.ssh(unit_name, "sudo snap logs otel-ebpf-profiler")
    assert "Everything is ready. Begin running and processing data." in out


def test_deploy_pyroscope(juju: Juju, pyroscope_tester_charm):
    juju.deploy(pyroscope_tester_charm, PYRO_TESTER_APP_NAME)
    juju.wait(jubilant.all_active)


# def test_integrate_pyroscope(juju:Juju, pyroscope_tester_charm):
#     juju.integrate(APP_NAME, PYRO_TESTER_APP_NAME)
#     juju.wait(jubilant.all_active)
