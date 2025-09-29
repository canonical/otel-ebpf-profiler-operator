module "otel_ebpf_profiler" {
  source  = "../../terraform"
  model   = var.model
  channel = "2/edge"
}
