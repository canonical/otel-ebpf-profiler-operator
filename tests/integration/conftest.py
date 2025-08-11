import logging
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


@fixture
def pyroscope_tester_charm():
    # simple caching for local testing
    path = Path("./pyroscope-tester/pyroscope-tester_amd64.charm")
    if path.exists():
        return path.resolve()
    return pack("./pyroscope-tester/")
