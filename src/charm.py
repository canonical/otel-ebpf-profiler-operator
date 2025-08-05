#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""A Juju charm for OpenTelemetry Collector on machines."""

import logging
import subprocess
from typing import  Final

import ops
from charmlibs.pathops import LocalPath
from lib.charms.operator_libs_linux.v2 import snap
from ops.model import MaintenanceStatus

from snap_management import (
    SnapInstallError,
    SnapServiceError,
    SnapSpecError,
    install_snap,
)

logger = logging.getLogger(__name__)

SERVER_CERT_PATH: Final[str] = (
    "/usr/local/share/ca-certificates/juju_tls-certificates/otlp_ebpf_profiler-server.crt"
)
SERVER_CERT_PRIVATE_KEY_PATH: Final[str] = "/etc/otlp_ebpf_profiler/private.key"


def is_tls_ready() -> bool:
    """Return True if the server cert and private key are present on disk."""
    return (
        LocalPath(SERVER_CERT_PATH).exists() and LocalPath(SERVER_CERT_PRIVATE_KEY_PATH).exists()
    )


def refresh_certs():
    """Run `update-ca-certificates` to refresh the trusted system certs."""
    subprocess.run(["update-ca-certificates", "--fresh"], check=True)


class OtlpEbpfProfilerCharm(ops.CharmBase):
    """Charm the service."""
    _snap_name = "otlp-ebpf-profiler"

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        if not self.unit.is_leader():
            self.unit.status = ops.BlockedStatus("This charm doesn't support being scaled.")
            return

        # we split events in three categories:
        # events on which we need to setup things
        for setup_evt in (self.on.upgrade_charm, self.on.install):
            framework.observe(setup_evt, self._on_setup_evt)

        # events on which we need to remove things
        for teardown_evt in (self.on.upgrade_charm, self.on.install):
            framework.observe(teardown_evt, self._on_teardown_evt)

        # events on which we may need to configure things
        for maintenance_evt in self.on.events().values():
            if not issubclass(maintenance_evt.event_type, ops.LifecycleEvent):
                framework.observe(maintenance_evt, self._on_maintenance_evt)

        framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)


    # event handlers
    def _on_setup_evt(self, _:ops.EventBase):
        self._setup()

    def _on_teardown_evt(self, _:ops.EventBase):
        self._teardown()

    def _on_maintenance_evt(self, _:ops.EventBase):
        self._reconcile()

    # lifecycle managers
    def _setup(self):
        """Install the snap."""
        self.unit.status = MaintenanceStatus(f"Installing {self._snap_name} snap")
        install_snap(self._snap_name)
        # Start the snap
        self.unit.status = MaintenanceStatus(f"Starting {self._snap_name} snap")
        try:
            self.snap().start(enable=True)
        except snap.SnapError as e:
            raise SnapServiceError(f"Failed to start {self._snap_name}") from e

    def _teardown(self):
        """Remove the snap."""
        self.unit.status = MaintenanceStatus(f"Uninstalling {self._snap_name} snap")
        try:
            self.snap().ensure(state=snap.SnapState.Absent)
        except (snap.SnapError, SnapSpecError) as e:
            raise SnapInstallError(f"Failed to uninstall {self._snap_name}") from e

    def _reconcile(self):
        pass

    def snap(self)-> snap.Snap:
        """Return the snap object.

        This method provides lazy initialization of snap objects, avoiding unnecessary
        calls to snapd until they're actually needed.
        """
        return snap.SnapCache()[self._snap_name]


    def _on_collect_unit_status(self, e: ops.CollectStatusEvent):
        e.add_status(ops.ActiveStatus(""))


if __name__ == "__main__":  # pragma: nocover
    ops.main(OtlpEbpfProfilerCharm)
