from unittest.mock import patch

import pytest

import machine_lock


@pytest.fixture(params=("foo", "bar-1231241-postgresql-0"))
def lock(request):
    return machine_lock.MachineLock(request.param)


@pytest.fixture(autouse=True)
def lockfile(tmp_path):
    pth = tmp_path/"machinelocktest.txt"
    with patch.object(machine_lock, "MACHINE_LOCK_PATH", pth):
        yield pth


def test_lock_acquire(lock, lockfile):
    # GIVEN no lock
    assert not lockfile.exists()
    # WHEN we acquire it
    acquired= lock.acquire()
    # THEN we have the lock
    assert acquired
    assert lockfile.read_text() == lock._fingerprint


@pytest.mark.parametrize("other_owner", ("someone-else", "not-me"))
def test_lock_acquire_fail(lock, lockfile, other_owner):
    # GIVEN the lock is set to someone else
    lockfile.write_text(other_owner)
    # WHEN we acquire it
    acquired = lock.acquire()
    # THEN we don't have the lock
    assert not acquired
    assert lockfile.read_text() == other_owner


def test_lock_acquire_own_already(lock, lockfile):
    # GIVEN the lock is set to ourselves already
    lockfile.write_text(lock._fingerprint)
    # WHEN we acquire it
    acquired = lock.acquire()
    # THEN we still have the lock
    assert acquired
    assert lockfile.read_text() == lock._fingerprint
