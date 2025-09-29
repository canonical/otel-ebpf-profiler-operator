import os
import shlex
import subprocess
from pathlib import Path

import jubilant
import pytest

from pytest_bdd import given, when, then


TESTS_DIR = Path(__file__).parent.resolve()
CHARM_CHANNEL = os.getenv("CHARM_CHANNEL", "2/edge")


@pytest.fixture(scope="module")
def juju():
    with jubilant.temp_model() as tm:
        yield tm


@given("a machine model")
@when("you run terraform apply using the provided module")
def test_terraform_apply(juju):
    subprocess.run(shlex.split(f"terraform -chdir={TESTS_DIR} init"), check=True)
    subprocess.run(
        shlex.split(
            f'terraform -chdir={TESTS_DIR} apply -var="channel={CHARM_CHANNEL}" '
            f'-var="model={juju.model}" -auto-approve'
        ),
        check=True,
    )


@then("the otel-ebpf-profiler charm is deployed and active")
def test_active(juju):
    juju.wait(lambda status: jubilant.all_active(status, "otel-ebpf-profiler"), timeout=60 * 10)
