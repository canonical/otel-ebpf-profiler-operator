from collections import namedtuple
from unittest.mock import patch

import pytest

import snap_management

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
