import logging
import os
from pathlib import Path
import platform
from pytest_jubilant import pack
from pytest import fixture
from jubilant import Juju
from tenacity import retry, stop_after_attempt, wait_fixed
import yaml

logger = logging.getLogger("conftest")
REPO_ROOT = Path(__file__).parent.parent.parent
METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = "profiler"
# get the charm os base without the trailing `:architecture` part
APP_BASE = next(iter(METADATA["platforms"])).split(":")[0]
OTEL_COLLECTOR_APP_NAME = "opentelemetry-collector"
COS_CHANNEL = "2/edge"


def get_system_arch() -> str:
    """Returns the architecture of this machine, mapping some values to amd64 or arm64.

    If platform is x86_64 or amd64, it returns amd64.
    If platform is aarch64, arm64, armv8b, or armv8l, it returns arm64.
    """
    arch = platform.machine().lower()
    if arch in ["x86_64", "amd64"]:
        arch = "amd64"
    elif arch in ["aarch64", "arm64", "armv8b", "armv8l"]:
        arch = "arm64"
    # else: keep arch as is
    return arch


@fixture(scope="module")
def patch_update_status_interval(juju: Juju):
    juju.model_config({"update-status-hook-interval": "1h"})
    yield
    juju.model_config(reset="update-status-hook-interval")


@retry(stop=stop_after_attempt(2), wait=wait_fixed(10))
def patch_otel_collector_log_level(juju: Juju, unit_no=0):
    # patch the collector's log level to INFO; we need this so that we can inspect the telemetry being dumped by the `debug` exporter
    # TODO: avoid this patch if possible, cfr. https://github.com/canonical/opentelemetry-collector-operator/issues/83
    juju.ssh(
        f"{OTEL_COLLECTOR_APP_NAME}/{unit_no}",
        f"sudo sed -i 's/level: WARN/level: INFO/' /etc/otelcol/config.d/{OTEL_COLLECTOR_APP_NAME}_{unit_no}.yaml",
    )
    # restart the snap for the updates to take place
    juju.ssh(f"{OTEL_COLLECTOR_APP_NAME}/{unit_no}", "sudo snap restart opentelemetry-collector")


@fixture(scope="module", autouse=True)
def patch_model_constraints_architecture(juju: Juju):
    juju.cli("set-model-constraints", f"arch={get_system_arch()}")


@fixture(scope="module")
def charm():
    """Charm used for integration testing."""
    if charm := os.getenv("CHARM_PATH"):
        logger.info("using charm from env")
        return charm
    if Path(charm := REPO_ROOT / "otel-ebpf-profiler_ubuntu@24.04-amd64.charm").exists():
        logger.info(f"using existing charm from {REPO_ROOT}")
        return charm
    logger.info(f"packing from {REPO_ROOT}")
    return pack(REPO_ROOT)
