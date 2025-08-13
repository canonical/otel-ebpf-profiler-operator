import json
from unittest.mock import patch
import ops
from ops.testing import State, CharmEvents, Relation
import pytest

from charm import OtelEbpfProfilerCharm
from charms.operator_libs_linux.v2 import snap

# autouse the snap_mocks fixture in this whole module
pytestmark = pytest.mark.usefixtures("snap_mocks")


@pytest.mark.parametrize(
    "event",
    (
        CharmEvents.upgrade_charm(),
        CharmEvents.install(),
        CharmEvents.update_status(),
        CharmEvents.install(),
    ),
)
def test_blocked_if_fails_acquire_machine_lock(ctx, event, snap_mocks, mock_lockfile):
    # GIVEN the machine lock is taken
    mock_lockfile.write_text("someone-else")
    # WHEN we receive any event
    state_out = ctx.run(event, State(leader=False))
    # THEN the unit sets blocked
    assert isinstance(state_out.unit_status, ops.BlockedStatus)


@pytest.mark.parametrize(
    "event",
    (
        CharmEvents.upgrade_charm(),
        CharmEvents.install(),
        CharmEvents.update_status(),
        CharmEvents.install(),
    ),
)
def test_snap_not_installed_if_fails_acquire_machine_lock(ctx, event, snap_mocks, mock_lockfile):
    # GIVEN the machine lock is taken
    mock_lockfile.write_text("someone-else")
    # WHEN we receive any event
    ctx.run(event, State(leader=False))
    # THEN the unit won't attempt to install or start the snap
    assert not snap_mocks.snap_mgmt.install_snap.called
    assert not snap_mocks.charm_snap.return_value.start.called


@pytest.mark.parametrize("event", (CharmEvents.upgrade_charm(), CharmEvents.install()))
def test_smoke(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive any event
    state_out = ctx.run(event, State(leader=True))
    # THEN the unit sets active
    assert state_out.unit_status == ops.ActiveStatus("profiling machine <testing>")


@pytest.mark.parametrize("event", (CharmEvents.upgrade_charm(), CharmEvents.install()))
def test_install_snap(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive any event
    state_out = ctx.run(event, State(leader=True))
    # THEN the unit will install or start the snap
    assert (
        ops.MaintenanceStatus(f"Installing {OtelEbpfProfilerCharm._snap_name} snap")
        in ctx.unit_status_history
    )
    assert state_out.unit_status == ops.ActiveStatus("profiling machine <testing>")
    assert snap_mocks.snap_mgmt.install_snap.called
    assert snap_mocks.charm_snap.return_value.start.called


@pytest.mark.parametrize("event", (CharmEvents.stop(), CharmEvents.remove()))
def test_remove_snap(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive the stop/remove event
    state_out = ctx.run(event, State(leader=True))
    # THEN the unit will install or start the snap
    assert (
        ops.MaintenanceStatus(f"Uninstalling {OtelEbpfProfilerCharm._snap_name} snap")
        in ctx.unit_status_history
    )
    assert state_out.unit_status == ops.ActiveStatus("profiling machine <testing>")
    assert snap_mocks.snap_mgmt.cleanup_config.called
    assert snap_mocks.charm_snap.return_value.ensure.called_with_args(state=snap.SnapState.Absent)


@pytest.mark.parametrize("event", (CharmEvents.update_status(),))
@pytest.mark.parametrize("changes", (True, False))
def test_config_reload(ctx, event, snap_mocks, changes):
    snap_mocks.snap_mgmt.update_config.return_value = changes
    # GIVEN the unit is leader
    # WHEN we receive any maintenance event
    state_out = ctx.run(event, State(leader=True))
    # THEN we'll call update_config and reload if there are changes
    if changes:
        assert snap_mocks.snap_mgmt.reload.called_with_args(
            OtelEbpfProfilerCharm._snap_name, OtelEbpfProfilerCharm._service_name
        )
        assert ops.MaintenanceStatus("Reloading snap config") in ctx.unit_status_history
    else:
        assert not snap_mocks.snap_mgmt.reload.called

    assert state_out.unit_status == ops.ActiveStatus("profiling machine <testing>")


def test_charm_tracing_configured(ctx):
    # GIVEN a cos_agent integration
    # AND remote has published a tracing endpoint
    url = "1.2.3.4:4318"
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
