#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
"""A Juju charm for OpenTelemetry eBPF Profiler on machines."""

import logging
import os

import cosl
import ops
import ops_tracing

from charms.operator_libs_linux.v2 import snap
from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointRequirer
from config_manager import ConfigManager
from config_builder import Port
from ops.model import MaintenanceStatus
from charms.grafana_agent.v0.cos_agent import COSAgentProvider, charm_tracing_config
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from constants import CA_CERT_PATH

import snap_management
from machine_lock import MachineLock

logger = logging.getLogger(__name__)


class OtelEbpfProfilerCharm(ops.CharmBase):
    """Charm the service."""

    _snap_name = "otel-ebpf-profiler"
    _service_name = "otel-ebpf-profiler"

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        if not MachineLock(cosl.JujuTopology.from_charm(self).identifier).acquire():
            self.unit.status = ops.BlockedStatus(
                "Unable to run on this machine, is already being profiled by another instance."
            )
            return
        self._should_reload_snap = False
        self._profiling_requirer = ProfilingEndpointRequirer(self.model.relations["profiling"])
        self._cos_agent = COSAgentProvider(
            self,
            # FIXME: uncomment when https://github.com/canonical/opentelemetry-collector-operator/issues/61 is fixed
            # tracing_protocols=["otlp_http"],
            metrics_endpoints=[{"path": "/metrics", "port": int(Port.metrics)}],
            # since otel-ebpf-profiler is a classic snap, we don't need to specify `log_slots`.
            # cos_agent will instead scrape the snap's dumped logs from /var/log/**
            log_slots=None,
        )
        self._cert_transfer = CertificateTransferRequires(self, "receive-ca-cert")

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
    def _on_setup_evt(self, _: ops.EventBase):
        self._setup()

    def _on_teardown_evt(self, _: ops.EventBase):
        self._teardown()

    def _on_maintenance_evt(self, _: ops.EventBase):
        self._reconcile()

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
        self._reconcile_certs()
        self._reconcile_charm_tracing()
        self._reconcile_config()
        if self._should_reload_snap:
            self._reload_snap()

    def _reconcile_certs(self):
        """Configure certs, which are transferred from a certificate_transfer provider, on disk."""
        certificates = self._cert_transfer.get_all_certificates()
        if certificates:
            combined_ca = "".join(cert + "\n\n" for cert in sorted(certificates))
            current_combined_ca = CA_CERT_PATH.read_text() if CA_CERT_PATH.exists() else ""
            if current_combined_ca != combined_ca:
                logger.debug("Updating CA file")
                CA_CERT_PATH.parent.mkdir(parents=True, exist_ok=True)
                CA_CERT_PATH.write_text(combined_ca)
                self._should_reload_snap = True
        else:
            CA_CERT_PATH.unlink(missing_ok=True)

    def _reconcile_charm_tracing(self):
        """Configure ops.tracing to send traces to a tracing backend."""
        endpoint, ca_cert_path = charm_tracing_config(self._cos_agent, CA_CERT_PATH)
        if not endpoint:
            return
        ops_tracing.set_destination(
            url=endpoint + "/v1/traces",
            ca=ca_cert_path,
        )

    def _reconcile_config(self):
        """Configure the otel collector config."""
        config_manager = ConfigManager()
        config_manager.add_topology_labels(cosl.JujuTopology.from_charm(self).as_dict())

        # Profiling integration
        config_manager.add_profile_forwarding(self._profiling_requirer.get_endpoints())

        # If the config file hash has changed, restart the snap
        config = config_manager.build()
        if snap_management.update_config(config.config, config.hash):
            self._should_reload_snap = True

    def _reload_snap(self):
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
