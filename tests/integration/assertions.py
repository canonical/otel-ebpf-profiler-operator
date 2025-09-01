#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

from typing import List
from jubilant import Juju
from conftest import OTEL_COLLECTOR_APP_NAME


def assert_pattern_in_snap_logs(juju: Juju, grep_filters: List[str]):
    cmd = (
        "sudo snap logs opentelemetry-collector -n=all"
        + " | "
        + " | ".join([f"grep {p}" for p in grep_filters])
    )
    otelcol_logs = juju.ssh(f"{OTEL_COLLECTOR_APP_NAME}/0", command=cmd)
    assert otelcol_logs, f"Filters {grep_filters} not found in the {OTEL_COLLECTOR_APP_NAME} logs"
