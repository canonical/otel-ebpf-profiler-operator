#!/usr/bin/env python3
# Copyright 2025 pietro
# See LICENSE file for licensing details.

"""Charm the service."""

import logging
import shlex
import subprocess
from pathlib import Path

import ops
import yaml
from charms.pyroscope_coordinator_k8s.v0.profiling import ProfilingEndpointProvider

logger = logging.getLogger(__name__)
PYRO_VERSION = "1.14.0"
PYRO_CONFIG = {
    "server": {"http_listen_port": 4040},
    "memberlist": {"bind_port": 7947, "join_members": ["localhost:7947"]},
}


def _runcmd(s: str) -> str:
    return subprocess.run(shlex.split(s), text=True, capture_output=True).stdout


class PyroscopeTesterCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        self.unit.status = ops.MaintenanceStatus("installing pyroscope...")
        if not (config_path := Path("/etc/pyroscope/config.yml")).exists():
            _runcmd(
                f"wget https://github.com/grafana/pyroscope/releases/download/v{PYRO_VERSION}/pyroscope_{PYRO_VERSION}_linux_amd64.deb"
            )
            _runcmd(f"sudo dpkg -i pyroscope_{PYRO_VERSION}_linux_amd64.deb")
            config_path.write_text(yaml.safe_dump(PYRO_CONFIG))

        self.unit.status = ops.MaintenanceStatus("configuring...")
        self.unit.open_port("tcp", 4040)

        own_IP = _runcmd("hostname -I").split()[0]

        profiling = ProfilingEndpointProvider(
            self.model.relations.get("profiling", []), app=self.app
        )
        profiling.publish_endpoint(f"{own_IP}:4040")

        self.unit.status = ops.ActiveStatus(
            f"pyroscope {PYRO_VERSION} ready at http://{own_IP}:4040"
        )


if __name__ == "__main__":  # pragma: nocover
    ops.main(PyroscopeTesterCharm)
