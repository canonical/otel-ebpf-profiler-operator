from pathlib import Path

import pytest
import jubilant
from jubilant import Juju
from pytest_jubilant import pack

from conftest import APP_NAME, sideload_snap
PYRO_TESTER_APP_NAME="pyro-tester"

@pytest.mark.setup
def test_deploy(juju: Juju, charm):
    juju.deploy(charm, APP_NAME, constraints={"virt-type": "virtual-machine"})
    juju.wait(lambda status: jubilant.all_blocked(status, APP_NAME))


def test_sideload_snap(juju: Juju, tmp_path):
    # FIXME: https://github.com/canonical/otel-ebpf-profiler-operator/issues/3
    unit_name = list(juju.status().apps[APP_NAME].units.keys())[0]

    sideload_snap(juju, tmp_path, unit_name)

    juju.wait(jubilant.all_active)


def test_profiler_running(juju: Juju):
    unit_name = list(juju.status().apps[APP_NAME].units.keys())[0]
    out = juju.ssh(unit_name, "sudo snap logs otel-ebpf-profiler")
    assert "Everything is ready. Begin running and processing data." in out


def test_deploy_pyroscope(juju:Juju, pyroscope_tester_charm):
    juju.deploy(pyroscope_tester_charm, PYRO_TESTER_APP_NAME)
    juju.wait(jubilant.all_active)


# def test_integrate_pyroscope(juju:Juju, pyroscope_tester_charm):
#     juju.integrate(APP_NAME, PYRO_TESTER_APP_NAME)
#     juju.wait(jubilant.all_active)
