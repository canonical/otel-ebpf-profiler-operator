Feature: profiling-tls

  Scenario: eBPF profiler is able to send system-wide profiles to a profiling backend over TLS
    Given an ebpf profiler charm is deployed on a juju virtual machine
    * an otel collector charm is deployed on the same machine
    * a certificates provider charm is deployed
    * the certificates provider charm is integrated with the collector to enable TLS
    * the certificates provider charm is integrated with the profiler to provide the CA
    When the profiler is integrated with the collector over profiling
    Then system-wide profiles are successfully pushed to the collector over TLS