"""Constants shared by this package."""

from typing import Final
from pathlib import Path

MACHINE_LOCK_PATH: Final[Path] = Path("/etc/otel-ebpf-profiler/machine.lock")
CA_CERT_PATH: Final[Path] = Path("/etc/otel-ebpf-profiler/receive-ca-cert.crt")
