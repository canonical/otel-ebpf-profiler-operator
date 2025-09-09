# Terraform module for otel-ebpf-profiler


This is a Terraform module facilitating the deployment of otel-ebpf-profiler charm, using the [Terraform juju provider](https://github.com/juju/terraform-provider-juju/). For more information, refer to the provider [documentation](https://registry.terraform.io/providers/juju/juju/latest/docs).


## Requirements
This module requires a `juju` model to be available. Refer to the [usage section](#usage) below for more details.

## API

### Inputs
The module offers the following configurable inputs:

| Name | Type | Description | Required |
| - | - | - | - |
| `app_name`| string | Application name | opentelemetry-collector |
| `channel`| string | Channel that the charm is deployed from |  |
| `config`| map(string) | Map of the charm configuration options | {} |
| `constraints`| string | Constraints for the Juju deployment| arch=amd64 |
| `model`| string | Name of the model that the charm is deployed on |  |
| `revision`| number | Revision number of the charm name | null |
| `storage_directives`| map(string) | Map of storage used by the application, which defaults to 1 GB, allocated by Juju | {} |
| `units`| number | Number of units to deploy | 1 |

### Outputs
Upon applied, the module exports the following outputs:

| Name        | Description |
|-------------| - |
| `app_name`  |  Application name |
| `endpoints` |  Map of `provides|requires` endpoints |

## Usage

Users should ensure that Terraform is aware of the `channel` and `juju_model` dependencies of the charm module.

To deploy this module, you can run `terraform apply -var="model_name=<MODEL_NAME>" -var "channel=2/edge" -auto-approve`


## Overriding constraints

By defaults, the `constraints` will instruct juju to provision for this charm a machine with the following constraints:
- `arch=amd64`
- `virt-type=virtual-machine`

The `virt-type` constraint should not be changed or removed, as deploying this charm to a container will result in a broken deployment. So, care must be taken to always include the `virt-type=virtual-machine` constraint when you are overriding the `constraints` tf variable.

For example, if you want to deploy `otel-ebpf-profiler` to a machine with a different architecture, you should set `constraints` to `arch=arm64,virt-type=virtual-machine`.

