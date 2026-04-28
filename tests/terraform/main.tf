module "otel-ebpf-profiler" {
  source     = "../../terraform"
  model_uuid = var.model_uuid
  channel    = var.channel
}
