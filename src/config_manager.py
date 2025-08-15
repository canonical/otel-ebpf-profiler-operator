"""Helper module to build the configuration for OpenTelemetry Collector."""

import logging
from collections import namedtuple
from typing import List, Dict


from config_builder import Component, ConfigBuilder

logger = logging.getLogger(__name__)

Config = namedtuple("Config", "config, hash")


class ConfigManager:
    """Configuration manager for OpenTelemetry Collector."""

    def __init__(
        self,
        insecure_skip_verify: bool = False,
    ):
        """Generate a default OpenTelemetry collector ConfigManager.

        The base configuration is our opinionated default.

        Args:
            insecure_skip_verify: value for `insecure_skip_verify` in all exporters
        """
        self._insecure_skip_verify = insecure_skip_verify
        self._config = ConfigBuilder(
            exporter_skip_verify=insecure_skip_verify,
        )

    def build(self) -> Config:
        """Return the built config and its hash."""
        cfg = self._config.build()
        return Config(cfg, self._config.hash(cfg))

    def add_topology_labels(self, topology_labels: Dict[str, str]):
        """Inject juju topology labels on the profile pipeline."""
        self._config.inject_topology_labels(topology_labels)

    def add_profile_forwarding(self, endpoints: List[str], tls: bool = False):
        """Configure forwarding profiles to a profiling backend (Pyroscope, Otelcol)."""
        for idx, endpoint in enumerate(endpoints):
            self._config.add_component(
                Component.exporter,
                # first component of this ID is the exporter type
                f"otlp/profiling/{idx}",
                {
                    "endpoint": endpoint,
                    # we likely need `insecure` as well as `insecure_skip_verify` because the endpoint
                    # we're receiving from pyroscope is a grpc one and has no scheme prefix, and probably
                    # the client defaults to https and fails to handshake unless we set `insecure=False`.
                    # FIXME: anyway for now pyroscope does not support TLS ingestion,
                    #  so we hardcode `insecure=True`.
                    #  once TLS support is implemented, we can uncomment the line below.
                    #  cfr: https://github.com/canonical/pyroscope-operators/pull/117
                    "tls": {
                        "insecure": True,
                        # "insecure": not tls,
                        "insecure_skip_verify": self._insecure_skip_verify,
                    },
                },
                pipelines=["profiles"],
            )
