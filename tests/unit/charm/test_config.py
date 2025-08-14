#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import yaml
from ops.testing import Relation, State
import pytest
from unittest.mock import patch


def get_updated_config(snap_mocks):
    """Intercept the snap_management.update_config(config, hash) call and return the config."""
    call_args = snap_mocks.snap_mgmt.update_config.call_args
    return yaml.safe_load(call_args[0][0])


@pytest.mark.parametrize("ca", (False, True))
@pytest.mark.parametrize("remote_tls", (False, True))
def test_profiling_exporter_config(ctx, snap_mocks, remote_tls, ca, mock_ca_cert):
    # GIVEN a profiling integration
    profiling_relation = Relation(
        endpoint="profiling",
        remote_app_data={
            "otlp_grpc_endpoint_url": json.dumps("grpc.server:1234"),
        },
    )
    # AND a receive-ca-cert integration IF ca is True
    receive_ca_relation = Relation(
        endpoint="receive-ca-cert",
        remote_app_data={"certificates": json.dumps(["cert1", "cert2"])},
    )
    relations = {profiling_relation}
    if ca:
        relations.add(receive_ca_relation)

    # WHEN we receive any event
    with patch("config_manager._is_tls", return_value=remote_tls):
        ctx.run(
            ctx.on.update_status(),
            state=State(relations=relations),
        )
    # THEN the updated config contains the profling otlp exporter
    # AND if the endpoint is behind TLS, insecure is set to True
    config = get_updated_config(snap_mocks)
    exporters = config["exporters"]
    assert "otlp/profiling/0" in exporters
    assert exporters["otlp/profiling/0"] == {
        "endpoint": "grpc.server:1234",
        "tls": {
            "insecure": not remote_tls,
            "insecure_skip_verify": False,
            **({"ca_file": str(mock_ca_cert)} if ca else {}),
        },
    }
