import subprocess
import jubilant
import pytest

from pytest_bdd import given, when, then


@pytest.fixture
def juju():
    yield from jubilant.temp_model()


@given("a machine model")
@when("you run terraform apply using the provided module")
def test_terraform_apply(juju):
    subprocess.run(["terraform", "init"])
    subprocess.run(
        [
            "terraform",
            "apply",
            '-var="channel=2/edge"',
            f'-var="model={juju.model}"',
            "-auto-approve",
        ]
    )


@then("the otel-ebpf-profiler charm is deployed and active")
def test_active(juju):
    juju.wait(jubilant.all_active, timeout=60 * 10)
