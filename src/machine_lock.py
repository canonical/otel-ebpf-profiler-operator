"""Simple machine lock to ensure each juju machine can only be claimed by a single unit."""

from typing import Optional

from constants import MACHINE_LOCK_PATH


class MachineLock:
    """Machine lock manager.

    Used to ensure that only a single unit of a charm can 'own' a juju machine.
    """

    def __init__(self, fingerprint: str):
        self._fingerprint = fingerprint

    def _get(self) -> Optional[str]:
        """Get current lock owner, if any."""
        return MACHINE_LOCK_PATH.read_text() if MACHINE_LOCK_PATH.exists() else None

    def _set(self):
        """Set the lock owner to yourself."""
        MACHINE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        MACHINE_LOCK_PATH.write_text(self._fingerprint)

    def acquire(self) -> bool:
        """Attempt to acquire machine lock, return whether the operation was successful.

        The idea is: only a single profiler per host machine can be active.
        We attempt to write to a predictable location a unique charm/unit fingerprint:
        - only the owner can remove it once the unit gets deleted.
        - if a unit finds in there a different fingerprint, it will error out.

        This helps manage the situation if the user scales up this charm, or deploys multiple
        instances of it to the same machine.
        Cfr. https://github.com/canonical/observability/pull/377
        """
        # this is guaranteed to be unique per controller; I guess it's a possibility that one
        # bootstraps multiple controllers to the same machine pool but in that case well,
        # you're on your own
        # juju guarantees this operation is as atomic as it needs to be, as no two units
        # will be running a hook at the same time on the same machine.
        lock = self._get()

        if lock is None:
            self._set()
            return True

        if lock == self._fingerprint:
            return True

        return False
