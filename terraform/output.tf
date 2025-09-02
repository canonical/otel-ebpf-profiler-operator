output "app_name" {
  value = juju_application.otel_ebpf_profiler.name
}

output "endpoints" {
  value = {
    # Requires
    profiling                   = "profiling",
    receive_ca_cert             = "receive-ca-cert",

    # Provides
    cos-agent                   = "cos-agent",
  }
}
