#!/usr/bin/env python3
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import patch
from ops.testing import Relation, State
import json


def test_charm_tracing_configured(ctx):
    # GIVEN a cos-agent integration
    # AND remote has published a tracing endpoint
    url = "http://1.2.3.4:4318"
    cos_agent_relation = Relation(
        endpoint="cos-agent",
        remote_units_data={
            0: {
                "receivers": json.dumps(
                    [{"protocol": {"name": "otlp_http", "type": "http"}, "url": url}]
                )
            }
        },
    )

    # WHEN we receive any event
    with patch("ops_tracing.set_destination") as p:
        ctx.run(
            ctx.on.update_status(),
            state=State(relations={cos_agent_relation}),
        )
    # THEN the charm has called ops_tracing.set_destination with the expected params
    p.assert_called_with(url=url + "/v1/traces", ca=None)
