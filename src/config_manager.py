"""Helper module to build the configuration for OpenTelemetry Collector."""

import logging
from collections import namedtuple
from typing import List


from config_builder import Component, ConfigBuilder

logger = logging.getLogger(__name__)

Config = namedtuple("Config", "config, hash")


class ConfigManager:
    """High-level configuration manager for OpenTelemetry Collector.

    This class provides a simplified interface for configuring the OpenTelemetry
    Collector by abstracting away the low-level details of the configuration format.
    It builds on top of the ConfigBuilder class to provide feature-oriented
    methods for common configuration scenarios.
    """

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
        """Return the built config."""
        cfg = self._config.build()
        return Config(cfg, self._config.hash(cfg))

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
