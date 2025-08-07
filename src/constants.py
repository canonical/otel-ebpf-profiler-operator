from typing import Final

SERVER_CERT_PATH: Final[str] = (
    "/usr/local/share/ca-certificates/juju_tls-certificates/otlp_ebpf_profiler-server.crt"
)
SERVER_CERT_PRIVATE_KEY_PATH: Final[str] = "/etc/otlp_ebpf_profiler/private.key"
MACHINE_LOCK_PATH: Final[str] = "/etc/otlp_ebpf_profiler/machine.lock"
