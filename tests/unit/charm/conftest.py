from collections import namedtuple
from unittest.mock import MagicMock, patch

from ops.testing import Context
import pytest

from charm import OtelEbpfProfilerCharm

SnapMocks = namedtuple("SnapMocks", "charm_snap, snap_mgmt")


@pytest.fixture(autouse=True)
def mock_lockfile(tmp_path):
    pth = tmp_path / "machinelocktest.txt"
    with patch("machine_lock.MACHINE_LOCK_PATH", pth):
        yield pth


@pytest.fixture(autouse=True)
def mock_ca_cert(tmp_path):
    tmp_ca_path = tmp_path / "ca.crt"
    with patch("charm.CA_CERT_PATH", tmp_ca_path):
        with patch("config_manager.CA_CERT_PATH", tmp_ca_path):
            yield tmp_ca_path


@pytest.fixture(autouse=True)
def snap_mocks():
    with (
        patch.object(OtelEbpfProfilerCharm, "snap", MagicMock()) as snapmock,
        patch("charm.snap_management", MagicMock()) as snapmgmmock,
    ):
        snapmgmmock.check_status.return_value = None
        yield SnapMocks(charm_snap=snapmock, snap_mgmt=snapmgmmock)


@pytest.fixture
def ctx():
    return Context(OtelEbpfProfilerCharm)
