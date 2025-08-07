#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""A Juju charm for OpenTelemetry Collector on machines."""

import logging
import subprocess

import ops
from charmlibs.pathops import LocalPath

# from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointRequirer
from charms.operator_libs_linux.v2 import snap
from config_manager import ConfigManager
from constants import SERVER_CERT_PATH, SERVER_CERT_PRIVATE_KEY_PATH
from ops.model import MaintenanceStatus

import snap_management

logger = logging.getLogger(__name__)


def is_tls_ready() -> bool:
    """Return True if the server cert and private key are present on disk."""
    return (
            LocalPath(SERVER_CERT_PATH).exists() and LocalPath(SERVER_CERT_PRIVATE_KEY_PATH).exists()
    )


def refresh_certs():
    """Run `update-ca-certificates` to refresh the trusted system certs."""
    subprocess.run(["update-ca-certificates", "--fresh"], check=True)


class OtelEbpfProfilerCharm(ops.CharmBase):
    """Charm the service."""
    _snap_name = "otel-ebpf-profiler"
    _service_name = "otel-ebpf-profiler"

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        if not self.unit.is_leader():
            self.unit.status = ops.BlockedStatus("This charm doesn't support being scaled.")
            return

        # TODO add profiling integration with:
        #   self._profiling_requirer = ProfilingEndpointRequirer(self.model.relations['profiling'])

        # we split events in three categories:
        # events on which we need to set up things
        for setup_evt in (self.on.upgrade_charm, self.on.install):
            framework.observe(setup_evt, self._on_setup_evt)

        # events on which we need to remove things
        for teardown_evt in (self.on.stop, self.on.remove):
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
        # for now we have to install it manually
        snap_management.install_snap(self._snap_name)
        # Start the snap
        self.unit.status = MaintenanceStatus(f"Starting {self._snap_name} snap")
        try:
            self.snap().start(enable=True)
        except snap.SnapError as e:
            raise snap_management.SnapServiceError(f"Failed to start {self._snap_name}") from e

    def _teardown(self):
        """Remove the snap and the config file."""
        self.unit.status = MaintenanceStatus(f"Uninstalling {self._snap_name} snap")
        try:
            self.snap().ensure(state=snap.SnapState.Absent)
        except (snap.SnapError, snap_management.SnapSpecError) as e:
            raise snap_management.SnapInstallError(f"Failed to uninstall {self._snap_name}") from e
        snap_management.cleanup_config()

    def _reconcile(self):
        config_manager = ConfigManager()
        # TODO: if profiling integration:
        #  call config_manager.add_profile_forwarding(otlp_grpc_endpoints)

        # If the config file or any cert has changed, a change in the hash
        # will trigger a restart
        config = config_manager.build()
        if snap_management.update_config(config.config, config.hash):
            self.unit.status = MaintenanceStatus("Reloading snap config")
            # this may raise; let the charm go to error state
            snap_management.reload(self._snap_name, self._service_name)

    def snap(self)-> snap.Snap:
        """Return the snap object.

        This method provides lazy initialization of snap objects, avoiding unnecessary
        calls to snapd until they're actually needed.
        """
        return snap.SnapCache()[self._snap_name]

    def _on_collect_unit_status(self, e: ops.CollectStatusEvent):
        # TODO: notify the user if there's no profiling relation
        e.add_status(ops.ActiveStatus(""))


if __name__ == "__main__":  # pragma: nocover
    ops.main(OtelEbpfProfilerCharm)
