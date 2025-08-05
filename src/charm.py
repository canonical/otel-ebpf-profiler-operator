#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""A Juju charm for OpenTelemetry Collector on machines."""

import logging
import subprocess

import ops
from charmlibs.pathops import LocalPath

from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointRequirer
from config_manager import ConfigManager
from constants import SERVER_CERT_PATH, SERVER_CERT_PRIVATE_KEY_PATH, CONFIG_FILE
from lib.charms.operator_libs_linux.v2 import snap
from ops.model import MaintenanceStatus

from snap_management import (
    SnapInstallError,
    SnapServiceError,
    SnapSpecError,
    install_snap,
)

logger = logging.getLogger(__name__)


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
    _snap_name = "opentelemetry-collector-ebpf-profiler"

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        if not self.unit.is_leader():
            self.unit.status = ops.BlockedStatus("This charm doesn't support being scaled.")
            return

        # TODO add profiling integration with:
        #   self._profiling_requirer = ProfilingEndpointRequirer(self.model.relations['profiling'])

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
        """Remove the snap and the config file."""
        self.unit.status = MaintenanceStatus(f"Uninstalling {self._snap_name} snap")
        try:
            self.snap().ensure(state=snap.SnapState.Absent)
        except (snap.SnapError, SnapSpecError) as e:
            raise SnapInstallError(f"Failed to uninstall {self._snap_name}") from e
        LocalPath(CONFIG_FILE).unlink(missing_ok=True)

    def _reconcile(self):
        config_manager = ConfigManager()
        # TODO: if profiling integration:
        #  call config_manager.add_profile_forwarding(otlp_grpc_endpoints)
        config = config_manager.build()
        LocalPath(CONFIG_FILE).write_text(config)

        # If the config file or any cert has changed, a change in the hash
        # will trigger a restart
        hash_file = LocalPath("/opt/otlp_ebpf_profiler_reload")
        old_hash = ""
        if hash_file.exists():
            old_hash = hash_file.read_text()
        current_hash = ",".join(
            [config_manager.hash()]
        )
        if current_hash != old_hash:
            # TODO: consider sending SIGHUP to otelcol svc to have it hot-reload any config changes instead of snap-restarting.
            self.snap().restart()
        hash_file.write_text(current_hash)

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
    ops.main(OtlpEbpfProfilerCharm)
