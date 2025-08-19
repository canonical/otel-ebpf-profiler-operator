import yaml
from ops.testing import State, CharmEvents
import pytest

from config_builder import TOPOLOGY_INJECTOR_PROCESSOR_NAME


def get_updated_config(snap_mocks):
    """Intercept the snap_management.update_config(config, hash) call and return the config."""
    call_args = snap_mocks.snap_mgmt.update_config.call_args
    return yaml.safe_load(call_args[0][0])


@pytest.mark.parametrize("event", (CharmEvents.update_status(), CharmEvents.config_changed()))
def test_config_topology_labels_processor(ctx, event, snap_mocks):
    # GIVEN the unit is leader
    # WHEN we receive any event
    ctx.run(event, State(leader=True))
    # THEN the updated config contains the topology label processor
    config = get_updated_config(snap_mocks)

    insert_keys = {
        attr["key"]
        for attr in config["processors"]["resource/profiling-topology-injector"]["attributes"]
        if attr["action"] == "insert"
    }
    assert insert_keys == {
        "juju_model",
        "juju_model_uuid",
        "juju_application",
        "juju_unit",
        "juju_charm_name",
    }
    assert TOPOLOGY_INJECTOR_PROCESSOR_NAME in config["processors"]
    assert (
        TOPOLOGY_INJECTOR_PROCESSOR_NAME
        in config["service"]["pipelines"]["profiles"]["processors"]
    )
