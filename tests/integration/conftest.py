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


def sideload_snap(tmp_path, unit_name):
    # FIXME: https://github.com/canonical/otel-ebpf-profiler-operator/issues/3
    if snap_path := os.getenv("SNAP_PATH"):
        step = f"juju scp {snap_path} {unit_name}:otel-ebpf-profiler.snap"
        logger.info(step)
        subprocess.run(shlex.split(step))
        return

    cwd = tmp_path / "snap"
    script = [
        "git clone https://github.com/canonical/otel-ebpf-profiler-snap --depth 1",
        "snapcraft pack"
        f"juju scp ./otel-ebpf-profiler_0.130.0_amd64.snap {unit_name}:otel-ebpf-profiler.snap",
    ]
    for step in script:
        logger.info(step)
        subprocess.run(shlex.split(step), cwd=cwd)
