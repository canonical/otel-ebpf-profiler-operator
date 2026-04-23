output "app_name" {
  value = juju_application.otel_ebpf_profiler.name
}

output "provides" {
  value = {
    cos-agent = "cos-agent",
  }
}

output "requires" {
  value = {
    profiling       = "profiling",
    receive_ca_cert = "receive-ca-cert",
  }
}
