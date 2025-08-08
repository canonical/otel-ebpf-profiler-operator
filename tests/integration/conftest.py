import logging
import shlex
import subprocess
import os
from pathlib import Path
from pytest_jubilant import pack
from pytest import fixture

logger = logging.getLogger("conftest")
APP_NAME = "profiler"


@fixture(scope="module")
def charm():
    """Charm used for integration testing."""
    if charm := os.getenv("CHARM_PATH"):
        logger.info("using charm from env")
        return charm
    if Path(charm := "./otel-ebpf-profiler_ubuntu@24.04-amd64.charm").exists():
        logger.info("using existing charm from ./")
        return charm
    logger.info("packing from ./")
    return pack("./")


def sideload_snap(juju, tmp_path, unit_name):
    # FIXME: https://github.com/canonical/otel-ebpf-profiler-operator/issues/3
    if snap_path := os.getenv("SNAP_PATH"):
        step = f"juju scp -m {juju.model} {snap_path} {unit_name}:/home/ubuntu/otel-ebpf-profiler.snap"
        logger.info(step)
        subprocess.run(shlex.split(step))
        return

    cwd = tmp_path / "snap"

    logger.info("cloning repo...")
    subprocess.run(
        shlex.split("git clone https://github.com/canonical/otel-ebpf-profiler-snap --depth 1"),
        cwd=cwd,
    )
    logger.info("packing...")
    cwd = cwd / "otel-ebpf-profiler-snap"
    subprocess.run(shlex.split("snapcraft pack"), cwd=cwd)
    logger.info("uploading snap...")
    subprocess.run(
        shlex.split(
            f"juju scp -m {juju.model}./otel-ebpf-profiler_0.130.0_amd64.snap {unit_name}:/home/ubuntu/otel-ebpf-profiler.snap"
        ),
        cwd=cwd,
    )

    # this is basically jhack fire install
    juju.ssh(
        unit_name,
        f"sudo /usr/bin/juju-exec -u {unit_name} "
        "JUJU_DISPATCH_PATH=hooks/install "
        f"JUJU_MODEL_NAME={juju.model} "
        f"JUJU_UNIT_NAME={unit_name} "
        f"/var/lib/juju/agents/unit-{unit_name.replace('/', '-')}/charm/dispatch",
    )


@fixture
def pyroscope_tester_charm():
    # simple caching for local testing
    path = Path("./pyroscope-tester/pyroscope-tester_amd64.charm")
    if path.exists():
        return path.resolve()
    return pack("./pyroscope-tester/")
