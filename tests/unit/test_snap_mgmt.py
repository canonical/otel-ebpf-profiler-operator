from collections import namedtuple
from unittest.mock import patch, MagicMock

import pytest

import snap_management
from charms.operator_libs_linux.v2.snap import SnapState

CfgMocks = namedtuple("CfgMocks", "config, hash")


@pytest.fixture
def mock_paths(tmp_path):
    with (
        patch.object(snap_management, "CONFIG_PATH", tmp_path / "config.yaml") as cfg,
        patch.object(snap_management, "HASH_LOCK_PATH", tmp_path / "hashlock.yaml") as hsh,
    ):
        yield CfgMocks(cfg, hsh)


def test_update_config_no_changes(mock_paths):
    # GIVEN an initial foo/foo content
    mock_paths.config.write_text("foo")
    mock_paths.hash.write_text("foo")

    # WHEN we call update_config with foo/foo
    snap_management.update_config("foo", "foo")

    # THEN no file is updated
    assert mock_paths.config.read_text() == "foo"
    assert mock_paths.hash.read_text() == "foo"


def test_update_only_hash_changed(mock_paths):
    # GIVEN an initial foo/foo content
    mock_paths.config.write_text("foo")
    mock_paths.hash.write_text("foo")

    # WHEN we call update_config with foo/bar (technically this shouldn't happen)
    snap_management.update_config("foo", "bar")

    # THEN the hash file is updated, but the config one remains the same (contents are identical)
    assert mock_paths.config.read_text() == "foo"
    assert mock_paths.hash.read_text() == "bar"


def test_update_config_changed_but_not_hash(mock_paths):
    # GIVEN an initial foo/foo content
    mock_paths.config.write_text("foo")
    mock_paths.hash.write_text("foo")

    # WHEN we call update_config with bar/foo (technically this shouldn't happen)
    snap_management.update_config("bar", "foo")

    # THEN no file is updated
    assert mock_paths.config.read_text() == "foo"
    assert mock_paths.hash.read_text() == "foo"


def test_happy_path(mock_paths):
    # GIVEN an initial foo/foo content
    mock_paths.config.write_text("foo")
    mock_paths.hash.write_text("foo")

    # WHEN we call update_config with bar/bar
    snap_management.update_config("bar", "bar")

    # THEN no file is updated
    assert mock_paths.config.read_text() == "bar"
    assert mock_paths.hash.read_text() == "bar"


def test_cleanup(mock_paths):
    # GIVEN an initial foo/foo content
    mock_paths.config.write_text("foo")
    mock_paths.hash.write_text("foo")

    # WHEN we call cleanup_config
    snap_management.cleanup_config()

    # THEN the files are gone
    assert not mock_paths.config.exists()
    assert not mock_paths.hash.exists()


def test_check_status_snap_absent(caplog):
    # GIVEN the snap is absent
    foo_snap = MagicMock()
    with patch("snap_management.SnapCache", return_value={"foo": foo_snap}):
        foo_snap.state = SnapState.Absent
        # WHEN we call check_status
        status = snap_management.check_status("foo", "bar")

    # THEN check_status returns an error message
    assert status is not None
    assert "snap is not installed" in status


def test_check_status_service_inactive(caplog):
    # GIVEN the snap service is inactive
    foo_snap = MagicMock()
    with patch("snap_management.SnapCache", return_value={"foo": foo_snap}):
        foo_snap.services = {"bar": {"active": False}}

        # WHEN we call check_status
        status = snap_management.check_status("foo", "bar")

    # THEN check_status returns an error message
    assert status is not None
    assert "snap is not running" in status


def test_check_status_bad_virt_type(caplog):
    # GIVEN a lxc virt-type
    foo_snap = MagicMock()
    with patch("snap_management.SnapCache", return_value={"foo": foo_snap}):
        foo_snap.services = {"bar": {"active": False}}
        with patch("subprocess.getoutput", return_value="lxc"):
            # WHEN we call check_status
            with caplog.at_level("ERROR"):
                caplog.clear()
                status = snap_management.check_status("foo", "bar")
                error_msgs = caplog.records

    # THEN check_status returns an error message
    assert status is not None
    assert "check host machine capabilities" in status
    # AND THEN we captured a log message about it too
    assert any("virt-type=virtual-machine" in emsg.message for emsg in error_msgs)


def test_check_status_not_running(caplog):
    # GIVEN the snap isn't running for any reason
    foo_snap = MagicMock()
    with patch("snap_management.SnapCache", return_value={"foo": foo_snap}):
        foo_snap.services = {"bar": {"active": False}}
        with patch("subprocess.getoutput", return_value="kvm"):
            # WHEN we call check_status
            status = snap_management.check_status("foo", "bar")

    # THEN check_status returns an error message
    assert status is not None
    assert "snap is not running" in status
