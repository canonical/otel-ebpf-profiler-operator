"""Helper module to build the configuration for OpenTelemetry Collector."""

import logging
from collections import namedtuple
import socket
import ssl
from typing import List
from constants import CA_CERT_PATH


from config_builder import Component, ConfigBuilder

logger = logging.getLogger(__name__)

Config = namedtuple("Config", "config, hash")


def _is_tls(endpoint: str):
    host, port = endpoint.rsplit(":", 1)
    port = int(port)
    try:
        ctx = ssl._create_unverified_context()
        with ctx.wrap_socket(
            socket.create_connection((host, port), timeout=3), server_hostname=host
        ):
            return True
    except ssl.SSLError:
        return False
    except Exception:
        return False


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

    def add_profile_forwarding(self, endpoints: List[str]):
        """Configure forwarding profiles to a profiling backend (Pyroscope, Otelcol)."""
        for idx, endpoint in enumerate(endpoints):
            self._config.add_component(
                Component.exporter,
                # first component of this ID is the exporter type
                f"otlp/profiling/{idx}",
                {
                    "endpoint": endpoint,
                    # we need `insecure` as well as `insecure_skip_verify` because the endpoint
                    # we're receiving from pyroscope/otelcol is a grpc one and has no scheme prefix, and
                    # the client defaults to https unless we set `insecure=False`.
                    "tls": {
                        "insecure": not _is_tls(endpoint),
                        "insecure_skip_verify": self._insecure_skip_verify,
                        **({"ca_file": str(CA_CERT_PATH)} if CA_CERT_PATH.exists() else {}),
                    },
                },
                pipelines=["profiles"],
            )
