
import ops
from ops.testing import State, CharmEvents
import pytest

from charm import OtlpEbpfProfilerCharm
from charms.operator_libs_linux.v2 import snap

# autouse the snap_mocks fixture in this whole module
pytestmark = pytest.mark.usefixtures("snap_mocks")

@pytest.mark.parametrize("event", (CharmEvents.upgrade_charm(), CharmEvents.install(), CharmEvents.update_status(), CharmEvents.install()))
def test_blocked_if_not_leader(ctx, event, snap_mocks):
    # GIVEN the unit is not leader
    # WHEN we receive any event
    state_out = ctx.run(event, State(leader=False))
    # THEN the unit sets blocked
    assert isinstance(state_out.unit_status, ops.BlockedStatus)


@pytest.mark.parametrize("event", (CharmEvents.upgrade_charm(), CharmEvents.install(), CharmEvents.update_status(), CharmEvents.install()))
def test_snap_not_installed_if_not_leader(ctx, event, snap_mocks):
    # GIVEN the unit is not leader
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
    assert state_out.unit_status==ops.ActiveStatus()


@pytest.mark.parametrize("event", (CharmEvents.upgrade_charm(), CharmEvents.install()))
def test_install_snap(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive any event
    state_out = ctx.run(event, State(leader=True))
    # THEN the unit will install or start the snap
    assert ops.MaintenanceStatus(f"Installing {OtlpEbpfProfilerCharm._snap_name} snap") in ctx.unit_status_history
    assert state_out.unit_status == ops.ActiveStatus()
    assert snap_mocks.snap_mgmt.install_snap.called
    assert snap_mocks.charm_snap.return_value.start.called


@pytest.mark.parametrize("event", (CharmEvents.stop(), CharmEvents.remove()))
def test_remove_snap(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive the stop/remove event
    state_out = ctx.run(event, State(leader=True))
    # THEN the unit will install or start the snap
    assert ops.MaintenanceStatus(f"Uninstalling {OtlpEbpfProfilerCharm._snap_name} snap") in ctx.unit_status_history
    assert state_out.unit_status == ops.ActiveStatus()
    assert snap_mocks.snap_mgmt.cleanup_config.called
    assert snap_mocks.charm_snap.return_value.ensure.called_with_args(state=snap.SnapState.Absent)


@pytest.mark.parametrize("event", (CharmEvents.update_status(), ))
@pytest.mark.parametrize("changes", (True, False))
def test_config_reload(ctx, event, snap_mocks, changes):
    snap_mocks.snap_mgmt.update_config.return_value = changes
    # GIVEN the unit is leader
    # WHEN we receive any maintenance event
    state_out = ctx.run(event, State(leader=True))
    # THEN we'll call update_config and reload if there are changes
    if changes:
        assert snap_mocks.snap_mgmt.reload.called_with_args(OtlpEbpfProfilerCharm._snap_name, OtlpEbpfProfilerCharm._service_name)
        assert ops.MaintenanceStatus("Reloading snap config") in ctx.unit_status_history
    else:
        assert not snap_mocks.snap_mgmt.reload.called

    assert state_out.unit_status == ops.ActiveStatus()



