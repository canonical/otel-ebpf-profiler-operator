#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""A Juju charm for OpenTelemetry eBPF Profiler on machines."""

import logging
import os

from cosl import JujuTopology
from cosl.reconciler import observe_events, reconcilable_events_machine

import ops

from charms.operator_libs_linux.v2 import snap
from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointRequirer
from config_manager import ConfigManager
from ops.model import MaintenanceStatus

import snap_management
from machine_lock import MachineLock

logger = logging.getLogger(__name__)


class OtelEbpfProfilerCharm(ops.CharmBase):
    """Charm the service."""

    _snap_name = "otel-ebpf-profiler"
    _service_name = "otel-ebpf-profiler"

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        if not MachineLock(JujuTopology.from_charm(self).identifier).acquire():
            self.unit.status = ops.BlockedStatus(
                "Unable to run on this machine, is already being profiled by another instance."
            )
            return

        self._profiling_requirer = ProfilingEndpointRequirer(self.model.relations["profiling"])

        # we split events in three categories:
        # events on which we need to set up things
        observe_events(self, (ops.UpgradeCharmEvent, ops.InstallEvent), self._setup)
        # events on which we need to tear down things
        observe_events(self, (ops.StopEvent, ops.RemoveEvent), self._teardown)
        # events on which we need to do regular config maintenance
        observe_events(self, reconcilable_events_machine, self._reconcile)

        framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)

    # lifecycle managers
    def _setup(self):
        """Install the snap."""
        self.unit.status = MaintenanceStatus(f"Installing {self._snap_name} snap")
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

        profiling_endpoints = [ep.otlp_grpc for ep in self._profiling_requirer.get_endpoints()]
        config_manager.add_profile_forwarding(profiling_endpoints)

        # If the config file hash has changed, restart the snap
        config = config_manager.build()
        if snap_management.update_config(config.config, config.hash):
            self.unit.status = MaintenanceStatus("Reloading snap config")
            # this may raise; let the charm go to error state
            snap_management.reload(self._snap_name, self._service_name)

        if not self.snap().services["otel-ebpf-profiler"]["active"]:
            # if at this point the snap isn't running, it could be because we've SIGHUPPED it too early
            # after installing it.
            self.snap().start(enable=True)

    def snap(self) -> snap.Snap:
        """Return the snap object.

        This method provides lazy initialization of snap objects, avoiding unnecessary
        calls to snapd until they're actually needed.
        """
        return snap.SnapCache()[self._snap_name]

    def _on_collect_unit_status(self, e: ops.CollectStatusEvent):
        # TODO: notify the user if there's no profiling relation

        # assumption: if this is a testing env, the envvar won't be set
        machine_id = os.getenv("JUJU_MACHINE_ID", "<testing>")
        # signal that this profiler instance owns an exclusive lock for profiling this machine
        e.add_status(ops.ActiveStatus(f"profiling machine {machine_id}"))


if __name__ == "__main__":  # pragma: nocover
    ops.main(OtelEbpfProfilerCharm)
