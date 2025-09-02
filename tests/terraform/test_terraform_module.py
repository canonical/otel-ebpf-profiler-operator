import subprocess
import jubilant

from pytest_bdd import given, when, then


@given("a machine model")
def test_setup_model():
    jubilant.Juju().add_model("test-terraform")


@when("you run terraform apply using the provided module")
def test_terraform_apply():
    subprocess.run(["terraform", "init"])
    subprocess.run(
        [
            "terraform",
            "apply",
            '-var="channel=2/edge"',
            '-var="model=test-terraform"',
            "-auto-approve",
        ]
    )


@then("the otel-ebpf-profiler charm is deployed and active")
def test_active():
    jubilant.Juju(model="test-terraform").wait(jubilant.all_active, timeout=60 * 10)


def test_teardown_model():
    jubilant.Juju().destroy_model("test-terraform")
