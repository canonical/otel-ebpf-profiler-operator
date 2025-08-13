import logging
import os
from pathlib import Path
from pytest_jubilant import pack
from pytest import fixture

logger = logging.getLogger("conftest")
APP_NAME = "profiler"
REPO_ROOT = Path(__file__).parent.parent.parent


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


@fixture
def pyroscope_tester_charm():
    # simple caching for local testing
    itest_root = REPO_ROOT / "tests" / "integration"
    path = itest_root / "pyroscope-tester" / "pyroscope-tester_amd64.charm"
    if path.exists():
        return path.resolve()
    return pack(itest_root / "pyroscope-tester")
