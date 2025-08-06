
from collections import namedtuple
from unittest.mock import MagicMock, patch

from ops.testing import Context
import pytest

from charm import OtlpEbpfProfilerCharm

SnapMocks = namedtuple("SnapMocks", "charm_snap, snap_mgmt")

@pytest.fixture
def snap_mocks():
    with (
        patch.object(OtlpEbpfProfilerCharm, "snap", MagicMock()) as snapmock,
        patch("charm.snap_management", MagicMock()) as snapmgmmock,
          ):
        yield SnapMocks(charm_snap=snapmock, snap_mgmt=snapmgmmock)


@pytest.fixture
def ctx():
    return Context(OtlpEbpfProfilerCharm)

