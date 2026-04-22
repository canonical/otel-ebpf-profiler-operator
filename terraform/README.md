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


<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | >= 0.15.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 0.15.0 |

## Modules

No modules.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name to give the deployed application | `string` | `"otel-ebpf-profiler"` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel that the charm is deployed from | `string` | n/a | yes |
| <a name="input_config"></a> [config](#input\_config) | Map of the charm configuration options | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | String listing constraints for this application | `string` | `"arch=amd64 virt-type=virtual-machine"` | no |
| <a name="input_model"></a> [model](#input\_model) | Reference to an existing model resource or data source for the model to deploy to | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |
| <a name="input_storage_directives"></a> [storage\_directives](#input\_storage\_directives) | Map of storage used by the application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_trust"></a> [trust](#input\_trust) | Whether this application is trusted to control the cluster | `bool` | `false` | no |
| <a name="input_units"></a> [units](#input\_units) | Unit count/scale | `number` | `1` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_name"></a> [app\_name](#output\_app\_name) | n/a |
| <a name="output_provides"></a> [provides](#output\_provides) | n/a |
| <a name="output_requires"></a> [requires](#output\_requires) | n/a |
<!-- END_TF_DOCS -->