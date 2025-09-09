resource "juju_application" "otel_ebpf_profiler" {
  name               = var.app_name
  config             = var.config
  constraints        = var.constraints
  model              = var.model
  storage_directives = var.storage_directives
  trust              = var.trust
  units              = var.units

  charm {
    name     = "otel-ebpf-profiler"
    channel  = var.channel
    revision = var.revision
  }
}
