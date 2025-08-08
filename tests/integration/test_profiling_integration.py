from jubilant import Juju


def test_deploy_pyroscope(juju: Juju):
    deploy_cmd = f'terraform apply -var="model={juju.model}" -auto-approve'