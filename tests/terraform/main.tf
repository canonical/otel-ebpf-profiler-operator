module "otel-ebpf-profiler" {
  source  = "../../terraform"
  model   = var.model
  channel = var.channel
}
